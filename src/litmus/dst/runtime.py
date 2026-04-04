from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from litmus.dst.faults import FaultPlan


@dataclass(slots=True)
class TraceEvent:
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BoundaryCoverage:
    detected: bool = False
    intercepted: bool = False
    simulated: bool = False
    faulted: bool = False
    unsupported: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "detected": self.detected,
            "intercepted": self.intercepted,
            "simulated": self.simulated,
            "faulted": self.faulted,
            "unsupported": self.unsupported,
        }


@dataclass(slots=True)
class RuntimeContext:
    seed: int
    fault_plan: FaultPlan
    trace: list[TraceEvent] = field(default_factory=list)
    resources: dict[tuple[str, int], object] = field(default_factory=dict)
    boundary_coverage: dict[str, BoundaryCoverage] = field(
        default_factory=lambda: {
            "http": BoundaryCoverage(),
            "sqlalchemy": BoundaryCoverage(),
            "redis": BoundaryCoverage(),
        }
    )

    def record(self, kind: str, **metadata: Any) -> None:
        if kind == "boundary_detected":
            boundary = str(metadata.get("boundary", "")).lower()
            if boundary in self.boundary_coverage:
                self.boundary_coverage[boundary].detected = True
        elif kind == "boundary_intercepted":
            boundary = str(metadata.get("boundary", "")).lower()
            if boundary in self.boundary_coverage:
                coverage = self.boundary_coverage[boundary]
                coverage.detected = True
                coverage.intercepted = True
        elif kind == "boundary_simulated":
            boundary = str(metadata.get("boundary", "")).lower()
            if boundary in self.boundary_coverage:
                coverage = self.boundary_coverage[boundary]
                coverage.detected = True
                coverage.intercepted = True
                coverage.simulated = True
        elif kind == "boundary_unsupported":
            boundary = str(metadata.get("boundary", "")).lower()
            if boundary in self.boundary_coverage:
                coverage = self.boundary_coverage[boundary]
                coverage.detected = True
                coverage.unsupported = True
        elif kind == "fault_injected":
            target = str(metadata.get("target", "")).lower()
            if target in self.boundary_coverage:
                self.boundary_coverage[target].faulted = True
        self.trace.append(TraceEvent(kind=kind, metadata=metadata))

    def mark_boundary_detected(self, boundary: str, *, detail: str | None = None) -> None:
        self._coverage(boundary).detected = True
        payload = {"boundary": boundary}
        if detail is not None:
            payload["detail"] = detail
        self.record("boundary_detected", **payload)

    def mark_boundary_intercepted(self, boundary: str, *, supported_shape: str) -> None:
        coverage = self._coverage(boundary)
        coverage.detected = True
        coverage.intercepted = True
        self.record(
            "boundary_intercepted",
            boundary=boundary,
            supported_shape=supported_shape,
        )

    def mark_boundary_simulated(self, boundary: str) -> None:
        coverage = self._coverage(boundary)
        coverage.detected = True
        coverage.intercepted = True
        coverage.simulated = True
        self.record("boundary_simulated", boundary=boundary)

    def mark_boundary_unsupported(self, boundary: str, *, detail: str) -> None:
        coverage = self._coverage(boundary)
        coverage.detected = True
        coverage.unsupported = True
        self.record(
            "boundary_unsupported",
            boundary=boundary,
            detail=detail,
        )

    def _coverage(self, boundary: str) -> BoundaryCoverage:
        if boundary not in self.boundary_coverage:
            self.boundary_coverage[boundary] = BoundaryCoverage()
        return self.boundary_coverage[boundary]
