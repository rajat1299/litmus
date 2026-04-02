from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from litmus.invariants.models import Invariant
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.replay.models import ReplayExplanation
from pydantic import BaseModel


@dataclass(slots=True)
class InvariantCounts:
    total: int
    confirmed: int
    suggested: int

    def to_dict(self) -> dict[str, int]:
        return {
            "total": self.total,
            "confirmed": self.confirmed,
            "suggested": self.suggested,
        }


@dataclass(slots=True)
class ReplayCounts:
    unchanged: int
    breaking: int
    benign: int
    improvement: int

    @classmethod
    def from_results(cls, replay_results) -> ReplayCounts:
        counts = Counter(replay.classification for replay in replay_results)
        return cls(
            unchanged=counts[ReplayClassification.UNCHANGED],
            breaking=counts[ReplayClassification.BREAKING_CHANGE],
            benign=counts[ReplayClassification.BENIGN_CHANGE],
            improvement=counts[ReplayClassification.IMPROVEMENT],
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "unchanged": self.unchanged,
            "breaking": self.breaking,
            "benign": self.benign,
            "improvement": self.improvement,
        }


@dataclass(slots=True)
class PropertyCounts:
    passed: int
    failed: int
    skipped: int

    @classmethod
    def from_results(cls, property_results) -> PropertyCounts:
        counts = Counter(result.status for result in property_results)
        return cls(
            passed=counts[PropertyCheckStatus.PASSED],
            failed=counts[PropertyCheckStatus.FAILED],
            skipped=counts[PropertyCheckStatus.SKIPPED],
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
        }


@dataclass(slots=True)
class InvariantView:
    name: str
    source: str
    status: str
    type: str
    reasoning: str | None
    method: str | None
    path: str | None

    @classmethod
    def from_invariant(cls, invariant: Invariant) -> InvariantView:
        request = invariant.request
        return cls(
            name=invariant.name,
            source=invariant.source,
            status=invariant.status.value,
            type=invariant.type.value,
            reasoning=invariant.reasoning,
            method=None if request is None or request.method is None else request.method.upper(),
            path=None if request is None else request.path,
        )

    def to_dict(self) -> dict[str, str | None]:
        payload: dict[str, str | None] = {
            "name": self.name,
            "source": self.source,
            "status": self.status,
            "type": self.type,
            "method": self.method,
            "path": self.path,
        }
        if self.reasoning is not None:
            payload["reasoning"] = self.reasoning
        return payload


@dataclass(slots=True)
class VerifyOperationResult:
    run_id: str
    app_reference: str
    scope_label: str
    routes: int
    invariants: InvariantCounts
    scenarios: int
    replay: ReplayCounts
    properties: PropertyCounts
    replay_seeds: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "app_reference": self.app_reference,
            "scope_label": self.scope_label,
            "routes": self.routes,
            "invariants": self.invariants.to_dict(),
            "scenarios": self.scenarios,
            "replay": self.replay.to_dict(),
            "properties": self.properties.to_dict(),
            "replay_seeds": list(self.replay_seeds),
        }


@dataclass(slots=True)
class ListInvariantsOperationResult:
    app_reference: str
    scope_label: str
    total: int
    invariants: list[InvariantView] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "app_reference": self.app_reference,
            "scope_label": self.scope_label,
            "total": self.total,
            "invariants": [invariant.to_dict() for invariant in self.invariants],
        }


@dataclass(slots=True)
class ReplayOperationResult:
    run_id: str
    source_run_id: str | None
    seed: str
    app_reference: str
    explanation: ReplayExplanation

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "run_id": self.run_id,
            "seed": self.seed,
            "app_reference": self.app_reference,
            "explanation": self.explanation.to_dict(),
        }
        if self.source_run_id is not None:
            payload["source_run_id"] = self.source_run_id
        return payload


@dataclass(slots=True)
class ExplainFailureOperationResult:
    seed: str
    source_run_id: str | None
    app_reference: str
    explanation: ReplayExplanation

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "seed": self.seed,
            "app_reference": self.app_reference,
            "explanation": self.explanation.to_dict(),
        }
        if self.source_run_id is not None:
            payload["source_run_id"] = self.source_run_id
        return payload


class InvariantCountsPayload(BaseModel):
    total: int
    confirmed: int
    suggested: int


class ReplayCountsPayload(BaseModel):
    unchanged: int
    breaking: int
    benign: int
    improvement: int


class PropertyCountsPayload(BaseModel):
    passed: int
    failed: int
    skipped: int


class InvariantViewPayload(BaseModel):
    name: str
    source: str
    status: str
    type: str
    reasoning: str | None = None
    method: str | None = None
    path: str | None = None


class ReplayResponsePayload(BaseModel):
    status_code: int | None
    body: object | None


class ReplayFaultContextPayload(BaseModel):
    selected_faults: list[str] = []
    injected_faults: list[str] = []
    defaulted_responses: list[str] = []
    app_exception: str | None = None


class ReplayExplanationPayload(BaseModel):
    seed: str
    method: str
    path: str
    classification: str
    baseline: ReplayResponsePayload
    current: ReplayResponsePayload
    reasons: list[str]
    fault_context: ReplayFaultContextPayload
    next_step: str
    trace_kinds: list[str]


class VerifyOperationPayload(BaseModel):
    run_id: str
    app_reference: str
    scope_label: str
    routes: int
    invariants: InvariantCountsPayload
    scenarios: int
    replay: ReplayCountsPayload
    properties: PropertyCountsPayload
    replay_seeds: list[str]

    @classmethod
    def from_operation(cls, result: VerifyOperationResult) -> VerifyOperationPayload:
        return cls.model_validate(result.to_dict())


class ListInvariantsOperationPayload(BaseModel):
    app_reference: str
    scope_label: str
    total: int
    invariants: list[InvariantViewPayload]

    @classmethod
    def from_operation(cls, result: ListInvariantsOperationResult) -> ListInvariantsOperationPayload:
        return cls.model_validate(result.to_dict())


class ReplayOperationPayload(BaseModel):
    run_id: str
    source_run_id: str | None = None
    seed: str
    app_reference: str
    explanation: ReplayExplanationPayload

    @classmethod
    def from_operation(cls, result: ReplayOperationResult) -> ReplayOperationPayload:
        return cls.model_validate(result.to_dict())


class ExplainFailureOperationPayload(BaseModel):
    seed: str
    source_run_id: str | None = None
    app_reference: str
    explanation: ReplayExplanationPayload

    @classmethod
    def from_operation(cls, result: ExplainFailureOperationResult) -> ExplainFailureOperationPayload:
        return cls.model_validate(result.to_dict())
