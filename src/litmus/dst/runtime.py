from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from litmus.dst.faults import FaultPlan


@dataclass(slots=True)
class TraceEvent:
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeContext:
    seed: int
    fault_plan: FaultPlan
    trace: list[TraceEvent] = field(default_factory=list)

    def record(self, kind: str, **metadata: Any) -> None:
        self.trace.append(TraceEvent(kind=kind, metadata=metadata))
