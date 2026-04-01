from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


_FIXED_APP_SOURCE = """\
from __future__ import annotations

import json
from typing import Any


class FastAPI:
    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Any] = {}

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


async def charge_with_retry(payload: dict[str, Any] | None) -> dict[str, Any]:
    amount = int((payload or {}).get("amount", 0))
    if amount > 500:
        return {"status_code": 402, "json": {"status": "declined"}}
    return {"status_code": 200, "json": {"status": "charged"}}


@app.post("/payments/charge")
async def charge(payload: dict[str, Any] | None) -> dict[str, Any]:
    return await charge_with_retry(payload)
"""


def test_payment_service_demo_fails_replays_and_passes_after_fix(tmp_path) -> None:
    source_repo = Path(__file__).resolve().parents[2] / "examples" / "payment_service"
    demo_repo = tmp_path / "payment_service"
    shutil.copytree(source_repo, demo_repo)

    verify_failure = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=demo_repo,
        check=False,
    )

    assert verify_failure.returncode == 1, verify_failure.stdout
    assert "App: app:app" in verify_failure.stdout
    assert "Routes: 1" in verify_failure.stdout
    assert "Invariants: 2" in verify_failure.stdout
    assert "Scenarios: 2" in verify_failure.stdout
    assert "Replay: unchanged=3 breaking=3 benign=0 improvement=0" in verify_failure.stdout
    assert "Properties: passed=0 failed=0 skipped=0" in verify_failure.stdout
    assert "Confidence: 0.50" in verify_failure.stdout

    replay_path = demo_repo / ".litmus" / "replay-traces.json"
    assert replay_path.exists()
    replay_data = json.loads(replay_path.read_text(encoding="utf-8"))
    assert replay_data["records"][0]["seed"] == "seed:1"

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=demo_repo,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Litmus replay" in replay_result.stdout
    assert "Seed: seed:1" in replay_result.stdout
    assert "Route: POST /payments/charge" in replay_result.stdout
    assert "Baseline: 200 {'status': 'charged'}" in replay_result.stdout
    assert "Current: 500 {'status': 'duplicate_charge_risk'}" in replay_result.stdout
    assert "Classification: breaking_change" in replay_result.stdout

    (demo_repo / "app.py").write_text(_FIXED_APP_SOURCE, encoding="utf-8")

    verify_fixed = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=demo_repo,
        check=False,
    )

    assert verify_fixed.returncode == 0, verify_fixed.stderr
    assert "Replay: unchanged=6 breaking=0 benign=0 improvement=0" in verify_fixed.stdout
    assert "Confidence: 1.00" in verify_fixed.stdout
