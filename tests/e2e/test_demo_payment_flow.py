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


def _assert_local_launch_budget(summary: dict[str, object]) -> None:
    performance = summary["performance"]
    assert performance == {
        "mode": "local",
        "fault_profile": "default",
        "budget_policy": "launch_default",
        "measured": True,
        "elapsed_ms": performance["elapsed_ms"],
        "budget_ms": 10_000,
        "within_budget": True,
        "replay_seeds_per_scenario": 3,
        "property_max_examples": 100,
    }
    assert isinstance(performance["elapsed_ms"], int)
    assert 0 <= performance["elapsed_ms"] <= performance["budget_ms"]


def test_payment_service_demo_fails_replays_and_passes_after_fix(tmp_path) -> None:
    source_repo = Path(__file__).resolve().parents[2] / "examples" / "payment_service"
    demo_repo = tmp_path / "payment_service"
    shutil.copytree(
        source_repo,
        demo_repo,
        ignore=shutil.ignore_patterns(".litmus", "__pycache__", "*.pyc"),
    )

    verify_failure = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=demo_repo,
        check=False,
    )

    assert verify_failure.returncode == 1, verify_failure.stdout
    assert "Litmus verify" in verify_failure.stdout
    assert "App: app:app" in verify_failure.stdout
    assert "Performance:" in verify_failure.stdout
    assert "budget<=10.00s mode=local profile=default within_budget=yes" in verify_failure.stdout
    assert "Launch budgets: replay_seeds/scenario=3 property_examples=100" in verify_failure.stdout
    assert "Budget policy: launch-default under-10s path" in verify_failure.stdout

    latest_run_id = json.loads((demo_repo / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads(
        (demo_repo / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8")
    )
    summary = run_payload["activities"][0]["summary"]
    assert summary["routes"] == 1
    assert summary["invariants"] == {
        "total": 2,
        "confirmed": 2,
        "suggested": 0,
    }
    assert summary["scenarios"] == 2
    assert summary["replay"] == {
        "unchanged": 1,
        "breaking_change": 1,
        "benign_change": 0,
        "improvement": 0,
    }
    assert summary["properties"] == {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
    }
    assert summary["confidence"] == 0.5
    _assert_local_launch_budget(summary)
    assert run_payload["artifacts"]["replay_traces"][0]["seed"] == "seed:1"
    assert not (demo_repo / ".litmus" / "replay-traces.json").exists()

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
    assert "Classification: breaking_change" in replay_result.stdout
    assert "- Status code regressed from 200 to 500." in replay_result.stdout

    (demo_repo / "app.py").write_text(_FIXED_APP_SOURCE, encoding="utf-8")

    verify_fixed = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=demo_repo,
        check=False,
    )

    assert verify_fixed.returncode == 0, verify_fixed.stderr
    assert "Litmus verify" in verify_fixed.stdout
    assert "Performance:" in verify_fixed.stdout
    assert "budget<=10.00s mode=local profile=default within_budget=yes" in verify_fixed.stdout
    assert "Budget policy: launch-default under-10s path" in verify_fixed.stdout
    latest_fixed_run_id = json.loads((demo_repo / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))[
        "run_id"
    ]
    fixed_run_payload = json.loads(
        (demo_repo / ".litmus" / "runs" / latest_fixed_run_id / "run.json").read_text(encoding="utf-8")
    )
    fixed_summary = fixed_run_payload["activities"][0]["summary"]
    assert fixed_summary["replay"] == {
        "unchanged": 2,
        "breaking_change": 0,
        "benign_change": 0,
        "improvement": 0,
    }
    assert fixed_summary["confidence"] == 1.0
    _assert_local_launch_budget(fixed_summary)
