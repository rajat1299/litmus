from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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
    defaulted_responses: list[str] = field(default_factory=list)
    app_exception: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "selected_faults": list(self.selected_faults),
            "injected_faults": list(self.injected_faults),
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
            defaulted_responses=list(payload.get("defaulted_responses", [])),
            app_exception=payload.get("app_exception"),
        )


@dataclass(slots=True)
class ReplayCheckpoint:
    kind: str
    target: str | None = None
    detail: str | None = None
    status_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": self.kind}
        if self.target is not None:
            payload["target"] = self.target
        if self.detail is not None:
            payload["detail"] = self.detail
        if self.status_code is not None:
            payload["status_code"] = self.status_code
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayCheckpoint:
        return cls(
            kind=payload["kind"],
            target=payload.get("target"),
            detail=payload.get("detail"),
            status_code=payload.get("status_code"),
        )


class ReplayFidelityStatus(str, Enum):
    MATCHED = "matched"
    DRIFTED = "drifted"
    NOT_CHECKED = "not_checked"


@dataclass(slots=True)
class ReplayFidelityResult:
    status: ReplayFidelityStatus
    recorded_step: int | None = None
    replay_step: int | None = None
    reason: str = ""
    recorded_checkpoint: ReplayCheckpoint | None = None
    replay_checkpoint: ReplayCheckpoint | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status.value,
            "reason": self.reason,
        }
        if self.recorded_step is not None:
            payload["recorded_step"] = self.recorded_step
        if self.replay_step is not None:
            payload["replay_step"] = self.replay_step
        if self.recorded_checkpoint is not None:
            payload["recorded_checkpoint"] = self.recorded_checkpoint.to_dict()
        if self.replay_checkpoint is not None:
            payload["replay_checkpoint"] = self.replay_checkpoint.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayFidelityResult:
        return cls(
            status=ReplayFidelityStatus(payload["status"]),
            recorded_step=payload.get("recorded_step"),
            replay_step=payload.get("replay_step"),
            reason=payload.get("reason", ""),
            recorded_checkpoint=None
            if payload.get("recorded_checkpoint") is None
            else ReplayCheckpoint.from_dict(payload["recorded_checkpoint"]),
            replay_checkpoint=None
            if payload.get("replay_checkpoint") is None
            else ReplayCheckpoint.from_dict(payload["replay_checkpoint"]),
        )


def replay_fidelity_not_checked() -> ReplayFidelityResult:
    return ReplayFidelityResult(
        status=ReplayFidelityStatus.NOT_CHECKED,
        reason="Recorded replay artifact predates execution fidelity transcripts.",
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
    fidelity: ReplayFidelityResult = field(default_factory=replay_fidelity_not_checked)
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
            "fidelity": self.fidelity.to_dict(),
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
            fidelity=ReplayFidelityResult.from_dict(payload["fidelity"])
            if "fidelity" in payload
            else replay_fidelity_not_checked(),
            next_step=payload.get("next_step", ""),
            trace_kinds=list(payload.get("trace_kinds", [])),
        )
