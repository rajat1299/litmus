from __future__ import annotations

import textwrap

from typer.testing import CliRunner

from litmus.cli import app


def test_litmus_watch_reruns_verification_on_python_change(tmp_path, monkeypatch) -> None:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
                    await send(
                        {
                            "type": "http.response.start",
                            "status": response["status_code"],
                            "headers": [(b"content-type", b"application/json")],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": json.dumps(response["json"]).encode("utf-8"),
                        }
                    )


            app = FastAPI()


            @app.post("/payments/charge")
            async def charge(payload):
                return {"status_code": 200, "json": {"status": "charged"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200_on_success():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"amount": 100},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    def fake_watch(*_args, **_kwargs):
        yield {("modified", str(service_dir / "app.py"))}

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr("litmus.watch.watch", fake_watch, raising=False)
    runner = CliRunner()

    result = runner.invoke(app, ["watch"])

    assert result.exit_code == 0, result.output
    assert "Watching for changes in" in result.output
    assert "Changed: service/app.py" in result.output
    assert "Litmus verify" in result.output
    assert "App: service.app:app" in result.output


def test_litmus_watch_ignores_litmus_artifacts(tmp_path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / ".litmus").mkdir()

    def fake_watch(*_args, **_kwargs):
        yield {("modified", str(repo_root / ".litmus" / "replay-traces.json"))}

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr("litmus.watch.watch", fake_watch, raising=False)
    runner = CliRunner()

    result = runner.invoke(app, ["watch"])

    assert result.exit_code == 0, result.output
    assert "Watching for changes in" in result.output
    assert "Changed:" not in result.output
    assert "Litmus verify" not in result.output
