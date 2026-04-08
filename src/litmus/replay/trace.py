from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from litmus.dst.faults import FaultPlan, FaultSpec
from litmus.dst.reachability import TargetSelectionArtifact
from litmus.dst.runtime import BoundaryCoverage, TraceEvent
from litmus.replay.models import ReplayCheckpoint, SchedulerDecision


@dataclass(slots=True)
class ReplayTraceRecord:
    seed: str
    seed_value: int
    app_reference: str
    method: str
    path: str
    request_payload: dict[str, Any] | None
    baseline_status_code: int | None
    baseline_body: dict[str, Any] | None
    trace: list[TraceEvent]
    scheduler_ledger: list[SchedulerDecision] | None = None
    replay_checkpoints: list[ReplayCheckpoint] | None = None
    execution_transcript: list[ReplayCheckpoint] | None = None
    target_selection: TargetSelectionArtifact | None = None


def replay_trace_record_to_dict(record: ReplayTraceRecord) -> dict[str, Any]:
    return {
        "seed": record.seed,
        "seed_value": record.seed_value,
        "app_reference": record.app_reference,
        "method": record.method,
        "path": record.path,
        "request_payload": record.request_payload,
        "baseline_status_code": record.baseline_status_code,
        "baseline_body": record.baseline_body,
        "trace": [
            {
                "kind": event.kind,
                "metadata": event.metadata,
            }
            for event in record.trace
        ],
        "scheduler_ledger": None
        if record.scheduler_ledger is None
        else [decision.to_dict() for decision in record.scheduler_ledger],
        "replay_checkpoints": None
        if record.replay_checkpoints is None
        else [checkpoint.to_dict() for checkpoint in record.replay_checkpoints],
        "execution_transcript": None
        if record.execution_transcript is None
        else [checkpoint.to_dict() for checkpoint in record.execution_transcript],
        "target_selection": None
        if record.target_selection is None
        else record.target_selection.to_dict(),
    }


def replay_trace_record_from_dict(payload: dict[str, Any]) -> ReplayTraceRecord:
    return ReplayTraceRecord(
        seed=payload["seed"],
        seed_value=payload["seed_value"],
        app_reference=payload["app_reference"],
        method=payload["method"],
        path=payload["path"],
        request_payload=payload.get("request_payload"),
        baseline_status_code=payload.get("baseline_status_code"),
        baseline_body=payload.get("baseline_body"),
        trace=[
            TraceEvent(kind=event["kind"], metadata=event.get("metadata", {}))
            for event in payload.get("trace", [])
        ],
        scheduler_ledger=None
        if payload.get("scheduler_ledger") is None
        else [
            SchedulerDecision.from_dict(decision_payload)
            for decision_payload in payload.get("scheduler_ledger", [])
        ],
        replay_checkpoints=None
        if payload.get("replay_checkpoints") is None
        else [
            ReplayCheckpoint.from_dict(checkpoint_payload)
            for checkpoint_payload in payload.get("replay_checkpoints", [])
        ],
        execution_transcript=None
        if payload.get("execution_transcript") is None
        else [
            ReplayCheckpoint.from_dict(checkpoint_payload)
            for checkpoint_payload in payload.get("execution_transcript", [])
        ],
        target_selection=None
        if payload.get("target_selection") is None
        else TargetSelectionArtifact.from_dict(payload["target_selection"]),
    )


def replay_fault_plan(record: ReplayTraceRecord) -> FaultPlan:
    if record.scheduler_ledger is not None:
        schedule = {
            decision.step: FaultSpec(
                kind=str(decision.detail),
                target=str(decision.target),
                params=dict(decision.params),
            )
            for decision in record.scheduler_ledger
            if decision.kind == "fault_plan_selected" and decision.step is not None and decision.target is not None
        }
        if schedule:
            return FaultPlan(seed=record.seed_value, schedule=schedule)

    for event in record.trace:
        if event.kind != "fault_plan_selected":
            continue

        schedule = {
            int(item["step"]): FaultSpec(
                kind=item["kind"],
                target=item["target"],
                params=dict(item.get("params", {})),
            )
            for item in event.metadata.get("schedule", [])
        }
        return FaultPlan(seed=record.seed_value, schedule=schedule)

    return FaultPlan(seed=record.seed_value)


def boundary_coverage_from_trace(trace: list[TraceEvent]) -> dict[str, BoundaryCoverage]:
    coverage = {
        "http": BoundaryCoverage(),
        "sqlalchemy": BoundaryCoverage(),
        "redis": BoundaryCoverage(),
    }
    for event in trace:
        if event.kind == "boundary_detected":
            coverage[event.metadata["boundary"]].detected = True
        elif event.kind == "boundary_intercepted":
            boundary = event.metadata["boundary"]
            coverage[boundary].detected = True
            coverage[boundary].intercepted = True
        elif event.kind == "boundary_simulated":
            boundary = event.metadata["boundary"]
            coverage[boundary].detected = True
            coverage[boundary].intercepted = True
            coverage[boundary].simulated = True
        elif event.kind == "boundary_unsupported":
            boundary = event.metadata["boundary"]
            coverage[boundary].detected = True
            coverage[boundary].unsupported = True
        elif event.kind == "fault_injected":
            boundary = event.metadata["target"]
            if boundary in coverage:
                coverage[boundary].faulted = True
    return coverage


def boundary_coverage_from_result(result) -> dict[str, BoundaryCoverage]:
    aggregate = {
        "http": BoundaryCoverage(),
        "sqlalchemy": BoundaryCoverage(),
        "redis": BoundaryCoverage(),
    }
    for record in result.replay_traces:
        trace_coverage = boundary_coverage_from_trace(record.trace)
        for boundary, snapshot in trace_coverage.items():
            current = aggregate[boundary]
            current.detected = current.detected or snapshot.detected
            current.intercepted = current.intercepted or snapshot.intercepted
            current.simulated = current.simulated or snapshot.simulated
            current.faulted = current.faulted or snapshot.faulted
            current.unsupported = current.unsupported or snapshot.unsupported
    return aggregate
