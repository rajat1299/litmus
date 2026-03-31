from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


def replay_trace_path(root: Path | str) -> Path:
    return Path(root) / ".litmus" / "replay-traces.json"


def save_replay_trace_records(root: Path | str, records: list[ReplayTraceRecord]) -> None:
    path = replay_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "records": [
            {
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
            for record in records
        ]
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_replay_trace_records(root: Path | str) -> list[ReplayTraceRecord]:
    path = replay_trace_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        ReplayTraceRecord(
            seed=item["seed"],
            seed_value=item["seed_value"],
            app_reference=item["app_reference"],
            method=item["method"],
            path=item["path"],
            request_payload=item.get("request_payload"),
            baseline_status_code=item.get("baseline_status_code"),
            baseline_body=item.get("baseline_body"),
            trace=[
                TraceEvent(kind=event["kind"], metadata=event.get("metadata", {}))
                for event in item.get("trace", [])
            ],
        )
        for item in data.get("records", [])
    ]


def replay_record_for_seed(root: Path | str, seed: str) -> ReplayTraceRecord:
    for record in load_replay_trace_records(root):
        if record.seed == seed:
            return record
    raise LookupError(f"could not find replay record for {seed}")
