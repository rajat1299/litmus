from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from litmus.dst.faults import FaultPlan, FaultSpec
from litmus.dst.runtime import TraceEvent


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
    )


def replay_fault_plan(record: ReplayTraceRecord) -> FaultPlan:
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
