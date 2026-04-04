from __future__ import annotations

from litmus.dst.reachability import PlannedFaultSeed, ScenarioReachability, TargetSelectionArtifact
from litmus.dst.runtime import TraceEvent
from litmus.replay.trace import ReplayTraceRecord, replay_fault_plan, replay_trace_record_from_dict, replay_trace_record_to_dict


def test_replay_fault_plan_reconstructs_schedule_from_trace_record() -> None:
    record = ReplayTraceRecord(
        seed="seed:7",
        seed_value=7,
        app_reference="service.app:app",
        method="GET",
        path="/health",
        request_payload=None,
        baseline_status_code=200,
        baseline_body={"status": "ok"},
        trace=[
            TraceEvent(
                kind="fault_plan_selected",
                metadata={
                    "schedule": [
                        {"step": 1, "target": "http", "kind": "timeout", "params": {}},
                        {"step": 2, "target": "http", "kind": "slow_response", "params": {"delay_ms": 50}},
                    ]
                },
            )
        ],
    )

    fault_plan = replay_fault_plan(record)

    assert fault_plan.seed == 7
    assert fault_plan.schedule[1].kind == "timeout"
    assert fault_plan.schedule[2].kind == "slow_response"
    assert fault_plan.schedule[2].params == {"delay_ms": 50}


def test_replay_trace_record_round_trips_target_selection_artifact() -> None:
    record = ReplayTraceRecord(
        seed="seed:3",
        seed_value=3,
        app_reference="service.app:app",
        method="POST",
        path="/payments/charge",
        request_payload={"payment_id": "ord-1"},
        baseline_status_code=200,
        baseline_body={"status": "charged"},
        trace=[TraceEvent(kind="request_started", metadata={"seed": 3})],
        target_selection=TargetSelectionArtifact.from_reachability(
            reachability=ScenarioReachability(
                clean_path_targets=("http",),
                fault_path_targets=("redis",),
                selected_targets=("http", "redis"),
            ),
            planned_fault_seed=PlannedFaultSeed(
                seed_value=3,
                target="redis",
                fault_kind="timeout",
                selection_source="fault_path",
            ),
        ),
    )

    restored = replay_trace_record_from_dict(replay_trace_record_to_dict(record))

    assert restored == record
