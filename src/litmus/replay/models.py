from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from litmus.replay.differential import ReplayClassification


@dataclass(slots=True)
class ReplayResponseDetails:
    status_code: int | None
    body: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "body": self.body,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayResponseDetails:
        return cls(
            status_code=payload.get("status_code"),
            body=payload.get("body"),
        )


@dataclass(slots=True)
class ReplayFaultContext:
    selected_faults: list[str] = field(default_factory=list)
    injected_faults: list[str] = field(default_factory=list)
    boundary_coverage: list[str] = field(default_factory=list)
    defaulted_responses: list[str] = field(default_factory=list)
    app_exception: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "selected_faults": list(self.selected_faults),
            "injected_faults": list(self.injected_faults),
            "boundary_coverage": list(self.boundary_coverage),
            "defaulted_responses": list(self.defaulted_responses),
        }
        if self.app_exception is not None:
            payload["app_exception"] = self.app_exception
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayFaultContext:
        return cls(
            selected_faults=list(payload.get("selected_faults", [])),
            injected_faults=list(payload.get("injected_faults", [])),
            boundary_coverage=list(payload.get("boundary_coverage", [])),
            defaulted_responses=list(payload.get("defaulted_responses", [])),
            app_exception=payload.get("app_exception"),
        )


@dataclass(slots=True)
class ReplayExplanation:
    seed: str
    method: str
    path: str
    classification: ReplayClassification
    baseline: ReplayResponseDetails
    current: ReplayResponseDetails
    reasons: list[str] = field(default_factory=list)
    fault_context: ReplayFaultContext = field(default_factory=ReplayFaultContext)
    next_step: str = ""
    trace_kinds: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "method": self.method,
            "path": self.path,
            "classification": self.classification.value,
            "baseline": self.baseline.to_dict(),
            "current": self.current.to_dict(),
            "reasons": list(self.reasons),
            "fault_context": self.fault_context.to_dict(),
            "next_step": self.next_step,
            "trace_kinds": list(self.trace_kinds),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayExplanation:
        return cls(
            seed=payload["seed"],
            method=payload["method"],
            path=payload["path"],
            classification=ReplayClassification(payload["classification"]),
            baseline=ReplayResponseDetails.from_dict(payload["baseline"]),
            current=ReplayResponseDetails.from_dict(payload["current"]),
            reasons=list(payload.get("reasons", [])),
            fault_context=ReplayFaultContext.from_dict(payload.get("fault_context", {})),
            next_step=payload.get("next_step", ""),
            trace_kinds=list(payload.get("trace_kinds", [])),
        )
