from __future__ import annotations

import subprocess
import textwrap


def test_litmus_replay_replays_a_recorded_breaking_scenario(tmp_path) -> None:
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
                return {"status_code": 500, "json": {"status": "broken"}}
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

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert verify_result.returncode == 1, verify_result.stdout

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Litmus replay" in replay_result.stdout
    assert "Seed: seed:1" in replay_result.stdout
    assert "Route: POST /payments/charge" in replay_result.stdout
    assert "Baseline: 200 {'status': 'charged'}" in replay_result.stdout
    assert "Current: 500 {'status': 'broken'}" in replay_result.stdout
    assert "Classification: breaking_change" in replay_result.stdout
    assert "Trace:" in replay_result.stdout
    assert "- request_started" in replay_result.stdout


def test_litmus_replay_reports_missing_artifact_cleanly(tmp_path) -> None:
    result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    assert "No replay traces found. Run `litmus verify` first." in result.stderr


def test_litmus_replay_reports_unknown_seed_cleanly(tmp_path) -> None:
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
                return {"status_code": 500, "json": {"status": "broken"}}
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

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert verify_result.returncode == 1, verify_result.stdout

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:99"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 1
    assert "No replay trace found for seed:99." in replay_result.stderr
