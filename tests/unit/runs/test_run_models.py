from __future__ import annotations

from litmus.dst.runtime import TraceEvent
from litmus.replay.models import ReplayCheckpoint, SchedulerDecision
from litmus.replay.trace import ReplayTraceRecord
from litmus.runs.models import (
    ActivityStatus,
    ActivityType,
    RunMode,
    RunStatus,
    VerificationActivity,
    VerificationRun,
)


def test_verification_run_round_trips_through_dict_payload() -> None:
    run = VerificationRun(
        run_id="run-123",
        mode=RunMode.LOCAL,
        status=RunStatus.COMPLETED,
        repo_root="/tmp/repo",
        app_reference="service.app:app",
        scope_label="full repo",
        started_at="2026-04-01T12:00:00+00:00",
        completed_at="2026-04-01T12:00:01+00:00",
        activities=[
            VerificationActivity(
                activity_id="verify-123",
                type=ActivityType.VERIFY,
                status=ActivityStatus.COMPLETED,
                started_at="2026-04-01T12:00:00+00:00",
                completed_at="2026-04-01T12:00:01+00:00",
                summary={"routes": 1, "confidence": 1.0},
            )
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:1",
                seed_value=1,
                app_reference="service.app:app",
                method="GET",
                path="/health",
                request_payload=None,
                baseline_status_code=200,
                baseline_body={"status": "ok"},
                trace=[TraceEvent(kind="request_started", metadata={"seed": 1})],
                scheduler_ledger=[
                    SchedulerDecision(kind="replay_seed", detail="seed:1"),
                    SchedulerDecision(kind="scenario", detail="GET /health"),
                    SchedulerDecision(kind="fault_plan_selected", step=1, target="http", detail="timeout"),
                ],
                replay_checkpoints=[
                    ReplayCheckpoint(kind="request_started", detail="GET /health"),
                    ReplayCheckpoint(kind="fault_injected", target="http", detail="timeout"),
                    ReplayCheckpoint(kind="response_completed", status_code=500),
                ],
            )
        ],
    )

    payload = run.to_dict()
    restored = VerificationRun.from_dict(payload)

    assert restored == run
