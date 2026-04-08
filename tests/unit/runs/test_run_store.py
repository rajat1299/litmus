from __future__ import annotations

import json

from litmus.dst.runtime import TraceEvent
from litmus.errors import ReplayLookupError
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
    load_verification_run,
    record_invariant_review_run,
    record_verification_run,
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
    except ReplayLookupError as exc:
        assert str(exc) == "No replay traces found. Run `litmus verify` first."
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected replay lookup without a replayable run to fail")


def test_replay_record_for_seed_raises_shared_error_for_unknown_seed(tmp_path) -> None:
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
        replay_traces=[],
    )

    save_verification_run(tmp_path, run, replayable=True)

    try:
        replay_record_for_seed(tmp_path, "seed:99")
    except ReplayLookupError as exc:
        assert str(exc) == "No replay trace found for seed:99."
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected replay lookup for an unknown seed to fail")


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


def test_record_invariant_review_run_persists_manifest_without_updating_latest_pointers(tmp_path) -> None:
    verification_run = VerificationRun(
        run_id="run-verify",
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
    save_verification_run(tmp_path, verification_run, replayable=True)

    review_run = record_invariant_review_run(
        tmp_path,
        invariant_name="charge_is_idempotent_on_retry",
        decision="dismissed",
        reason="Retry behavior is already enforced elsewhere.",
        review_source="cli",
    )

    assert load_latest_verification_run(tmp_path).run_id == "run-verify"
    assert load_latest_replayable_run(tmp_path).run_id == "run-verify"

    stored_review_run = load_verification_run(tmp_path, review_run.run_id)
    assert stored_review_run.app_reference is None
    assert stored_review_run.scope_label == "curated invariant review"
    assert stored_review_run.activities[0].type is ActivityType.INVARIANT_REVIEW
    assert stored_review_run.activities[0].summary == {
        "invariant_name": "charge_is_idempotent_on_retry",
        "decision": "dismissed",
        "review_source": "cli",
        "reason": "Retry behavior is already enforced elsewhere.",
    }


def test_record_verification_run_uses_measured_result_timing_in_summary(tmp_path) -> None:
    result = type(
        "Result",
        (),
        {
            "app_reference": "service.app:app",
            "scope_label": "full repo",
            "started_at": "2026-04-07T12:00:00+00:00",
            "completed_at": "2026-04-07T12:00:02.500000+00:00",
            "mode": "local",
            "fault_profile": "default",
            "replay_seeds_per_scenario": 3,
            "property_max_examples": 100,
            "routes": [],
            "invariants": [],
            "scenarios": [],
            "replay_results": [],
            "replay_traces": [],
            "property_results": [],
        },
    )()

    run = record_verification_run(tmp_path, result, mode=RunMode.LOCAL)

    assert run.started_at == "2026-04-07T12:00:00+00:00"
    assert run.completed_at == "2026-04-07T12:00:02.500000+00:00"
    assert run.activities[0].summary["performance"] == {
        "mode": "local",
        "fault_profile": "default",
        "budget_policy": "launch_default",
        "measured": True,
        "elapsed_ms": 2500,
        "budget_ms": 10000,
        "within_budget": True,
        "replay_seeds_per_scenario": 3,
        "property_max_examples": 100,
        "search_budget": {
            "requested_seeds_per_scenario": 3,
            "requested_total_replay_seeds": 0,
            "allocated_total_replay_seeds": 0,
            "executed_replays": 0,
            "scenarios_with_reachable_targets": 0,
            "scenarios_without_reachable_targets": 0,
            "target_single_scenarios": 0,
            "target_spread_scenarios": 0,
            "no_boundary_scenarios": 0,
            "disabled_scenarios": 0,
            "reduced_allocation_scenarios": 0,
            "redistributed_scenarios": 0,
            "frontier_capped_scenarios": 0,
            "multi_target_priority_scenarios": 0,
            "kind_diverse_priority_scenarios": 0,
            "unique_selected_targets": [],
            "unique_planned_fault_kinds": [],
            "kind_diverse_scenarios": 0,
        },
    }


def test_record_verification_run_marks_summary_performance_unmeasured_without_result_timestamps(tmp_path) -> None:
    result = type(
        "Result",
        (),
        {
            "app_reference": "service.app:app",
            "scope_label": "full repo",
            "mode": "local",
            "fault_profile": "default",
            "replay_seeds_per_scenario": 3,
            "property_max_examples": 100,
            "routes": [],
            "invariants": [],
            "scenarios": [],
            "replay_results": [],
            "replay_traces": [],
            "property_results": [],
        },
    )()

    run = record_verification_run(tmp_path, result, mode=RunMode.LOCAL)

    assert run.activities[0].summary["performance"] == {
        "mode": "local",
        "fault_profile": "default",
        "budget_policy": "launch_default",
        "measured": False,
        "elapsed_ms": None,
        "budget_ms": 10000,
        "within_budget": None,
        "replay_seeds_per_scenario": 3,
        "property_max_examples": 100,
        "search_budget": {
            "requested_seeds_per_scenario": 3,
            "requested_total_replay_seeds": 0,
            "allocated_total_replay_seeds": 0,
            "executed_replays": 0,
            "scenarios_with_reachable_targets": 0,
            "scenarios_without_reachable_targets": 0,
            "target_single_scenarios": 0,
            "target_spread_scenarios": 0,
            "no_boundary_scenarios": 0,
            "disabled_scenarios": 0,
            "reduced_allocation_scenarios": 0,
            "redistributed_scenarios": 0,
            "frontier_capped_scenarios": 0,
            "multi_target_priority_scenarios": 0,
            "kind_diverse_priority_scenarios": 0,
            "unique_selected_targets": [],
            "unique_planned_fault_kinds": [],
            "kind_diverse_scenarios": 0,
        },
    }
