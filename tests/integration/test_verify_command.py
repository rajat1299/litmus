from __future__ import annotations

import subprocess
import textwrap


def test_litmus_verify_runs_end_to_end_against_mined_scenarios(tmp_path) -> None:
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
                amount = payload["amount"]
                if amount > 500:
                    return {"status_code": 402, "json": {"status": "declined"}}
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


            def test_charge_returns_402_on_decline():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"amount": 1000},
                }
                response = {
                    "status_code": 402,
                    "json": {"status": "declined"},
                }

                assert response["status_code"] == 402
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "App: service.app:app" in result.stdout
    assert "Routes: 1" in result.stdout
    assert "Invariants: 2" in result.stdout
    assert "Scenarios: 2" in result.stdout
    assert "Replay: unchanged=2 breaking=0 benign=0 improvement=0" in result.stdout
    assert "Properties: passed=0 failed=0 skipped=0" in result.stdout
    assert "Confidence: 1.00" in result.stdout
