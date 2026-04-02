from __future__ import annotations

import json

from litmus.dst.runtime import TraceEvent
from litmus.replay.trace import ReplayTraceRecord
from litmus.runs.models import (
    ActivityStatus,
    ActivityType,
    RunMode,
    RunStatus,
    VerificationActivity,
    VerificationRun,
)
from litmus.runs.store import (
    clear_latest_replayable_run,
    latest_replayable_run_pointer_path,
    latest_run_pointer_path,
    load_latest_replayable_run,
    load_latest_verification_run,
    replay_record_for_seed,
    save_verification_run,
)


def test_save_verification_run_updates_latest_and_latest_replayable_pointers(tmp_path) -> None:
    run = VerificationRun(
        run_id="run-123",
        mode=RunMode.LOCAL,
        status=RunStatus.COMPLETED,
        repo_root=str(tmp_path),
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
            )
        ],
    )

    save_verification_run(tmp_path, run, replayable=True)

    assert latest_run_pointer_path(tmp_path).exists()
    assert latest_replayable_run_pointer_path(tmp_path).exists()
    assert load_latest_verification_run(tmp_path).run_id == "run-123"
    assert load_latest_replayable_run(tmp_path).run_id == "run-123"


def test_replay_record_for_seed_prefers_latest_replayable_run_over_latest_run(tmp_path) -> None:
    replayable_run = VerificationRun(
        run_id="run-verify",
        mode=RunMode.LOCAL,
        status=RunStatus.COMPLETED,
        repo_root=str(tmp_path),
        app_reference="service.app:app",
        scope_label="full repo",
        started_at="2026-04-01T12:00:00+00:00",
        completed_at="2026-04-01T12:00:01+00:00",
        activities=[],
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
                trace=[TraceEvent(kind="request_started")],
            )
        ],
    )
    replay_run = VerificationRun(
        run_id="run-replay",
        mode=RunMode.LOCAL,
        status=RunStatus.COMPLETED,
        repo_root=str(tmp_path),
        app_reference="service.app:app",
        scope_label="full repo",
        started_at="2026-04-01T12:00:02+00:00",
        completed_at="2026-04-01T12:00:03+00:00",
        activities=[
            VerificationActivity(
                activity_id="replay-123",
                type=ActivityType.REPLAY,
                status=ActivityStatus.COMPLETED,
                started_at="2026-04-01T12:00:02+00:00",
                completed_at="2026-04-01T12:00:03+00:00",
                seed="seed:1",
            )
        ],
    )

    save_verification_run(tmp_path, replayable_run, replayable=True)
    save_verification_run(tmp_path, replay_run, replayable=False)

    source_run, record = replay_record_for_seed(tmp_path, "seed:1")

    assert source_run.run_id == "run-verify"
    assert record.seed == "seed:1"


def test_replay_record_for_seed_raises_when_only_legacy_trace_file_exists_without_runs(tmp_path) -> None:
    trace_dir = tmp_path / ".litmus"
    trace_dir.mkdir()
    (trace_dir / "replay-traces.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "seed": "seed:1",
                        "seed_value": 1,
                        "app_reference": "service.app:app",
                        "method": "GET",
                        "path": "/health",
                        "request_payload": None,
                        "baseline_status_code": 200,
                        "baseline_body": {"status": "ok"},
                        "trace": [{"kind": "request_started", "metadata": {}}],
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        replay_record_for_seed(tmp_path, "seed:1")
    except FileNotFoundError:
        pass
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected replay lookup without a replayable run to fail")


def test_clear_latest_replayable_run_removes_only_replayable_pointer(tmp_path) -> None:
    run = VerificationRun(
        run_id="run-123",
        mode=RunMode.LOCAL,
        status=RunStatus.COMPLETED,
        repo_root=str(tmp_path),
        app_reference="service.app:app",
        scope_label="full repo",
        started_at="2026-04-01T12:00:00+00:00",
        completed_at="2026-04-01T12:00:01+00:00",
        activities=[],
    )
    save_verification_run(tmp_path, run, replayable=True)

    clear_latest_replayable_run(tmp_path)

    assert latest_run_pointer_path(tmp_path).exists()
    assert not latest_replayable_run_pointer_path(tmp_path).exists()
