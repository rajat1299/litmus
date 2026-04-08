from __future__ import annotations

from litmus.dst.reachability import PlannedFaultSeed, ScenarioReachability, TargetSelectionArtifact
from litmus.dst.runtime import TraceEvent
from litmus.replay.models import ReplayCheckpoint, ReplayResponseDetails, SchedulerDecision
from litmus.replay.trace import ReplayTraceRecord, replay_fault_plan, replay_trace_record_from_dict, replay_trace_record_to_dict
from litmus.search_budget import ScenarioSearchBudget


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


def test_replay_fault_plan_prefers_scheduler_ledger_when_present() -> None:
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
                    ]
                },
            )
        ],
        scheduler_ledger=[
            SchedulerDecision(kind="replay_seed", detail="seed:7"),
            SchedulerDecision(kind="scenario", detail="GET /health"),
            SchedulerDecision(kind="fault_plan_selected", step=1, target="redis", detail="timeout"),
            SchedulerDecision(
                kind="fault_plan_selected",
                step=2,
                target="redis",
                detail="slow_response",
                params={"delay_ms": 50},
            ),
        ],
    )

    fault_plan = replay_fault_plan(record)

    assert fault_plan.seed == 7
    assert fault_plan.schedule[1].target == "redis"
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
        scheduler_ledger=[
            SchedulerDecision(kind="replay_seed", detail="seed:3"),
            SchedulerDecision(kind="scenario", detail="POST /payments/charge"),
            SchedulerDecision(kind="fault_target_selected", target="redis", detail="fault_path"),
            SchedulerDecision(kind="fault_kind_selected", target="redis", detail="timeout"),
            SchedulerDecision(kind="fault_plan_selected", step=1, target="redis", detail="timeout"),
            SchedulerDecision(kind="fault_injected", step=1, target="redis", detail="timeout"),
        ],
        replay_checkpoints=[
            ReplayCheckpoint(kind="request_started", detail="POST /payments/charge"),
            ReplayCheckpoint(kind="boundary_enter", target="redis"),
            ReplayCheckpoint(kind="fault_injected", target="redis", detail="timeout"),
            ReplayCheckpoint(kind="boundary_exit", target="redis"),
            ReplayCheckpoint(kind="response_completed", status_code=500),
        ],
        recorded_outcome=ReplayResponseDetails(status_code=500, body={"status": "charged"}),
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
        search_budget=ScenarioSearchBudget(
            requested_seeds=3,
            allocated_seeds=3,
            redistributed_seeds=0,
            allocation_mode="target_spread",
            selected_targets=("http", "redis"),
            planned_fault_kinds=("timeout",),
            scenario_seed_start=1,
            scenario_seed_end=3,
        ),
    )

    restored = replay_trace_record_from_dict(replay_trace_record_to_dict(record))

    assert restored == record
