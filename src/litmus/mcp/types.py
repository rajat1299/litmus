from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from litmus.compatibility import CompatibilityReport
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
    pending_review: int

    def to_dict(self) -> dict[str, int]:
        return {
            "total": self.total,
            "confirmed": self.confirmed,
            "suggested": self.suggested,
            "pending_review": self.pending_review,
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
class BoundaryCoverageCounts:
    detected: bool
    intercepted: bool
    simulated: bool
    faulted: bool
    unsupported: bool

    @classmethod
    def from_mapping(cls, mapping) -> dict[str, BoundaryCoverageCounts]:
        return {
            boundary: cls(
                detected=coverage.detected,
                intercepted=coverage.intercepted,
                simulated=coverage.simulated,
                faulted=coverage.faulted,
                unsupported=coverage.unsupported,
            )
            for boundary, coverage in mapping.items()
        }

    def to_dict(self) -> dict[str, bool]:
        return {
            "detected": self.detected,
            "intercepted": self.intercepted,
            "simulated": self.simulated,
            "faulted": self.faulted,
            "unsupported": self.unsupported,
        }


@dataclass(slots=True)
class PerformanceCounts:
    mode: str
    fault_profile: str
    budget_policy: str
    search_strategy: str
    measured: bool
    elapsed_ms: int | None
    budget_ms: int
    within_budget: bool | None
    replay_seeds_per_scenario: int
    property_max_examples: int
    search_budget: SearchBudgetCounts

    def to_dict(self) -> dict[str, str | int | bool | None]:
        return {
            "mode": self.mode,
            "fault_profile": self.fault_profile,
            "budget_policy": self.budget_policy,
            "search_strategy": self.search_strategy,
            "measured": self.measured,
            "elapsed_ms": self.elapsed_ms,
            "budget_ms": self.budget_ms,
            "within_budget": self.within_budget,
            "replay_seeds_per_scenario": self.replay_seeds_per_scenario,
            "property_max_examples": self.property_max_examples,
            "search_budget": self.search_budget.to_dict(),
        }


@dataclass(slots=True)
class SearchBudgetCounts:
    requested_seeds_per_scenario: int
    requested_total_replay_seeds: int
    allocated_total_replay_seeds: int
    executed_replays: int
    scenarios_with_reachable_targets: int
    scenarios_without_reachable_targets: int
    target_single_scenarios: int
    target_spread_scenarios: int
    no_boundary_scenarios: int
    disabled_scenarios: int
    reduced_allocation_scenarios: int
    redistributed_scenarios: int
    frontier_capped_scenarios: int
    multi_target_priority_scenarios: int
    kind_diverse_priority_scenarios: int
    unique_selected_targets: list[str]
    unique_planned_fault_kinds: list[str]
    kind_diverse_scenarios: int

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_seeds_per_scenario": self.requested_seeds_per_scenario,
            "requested_total_replay_seeds": self.requested_total_replay_seeds,
            "allocated_total_replay_seeds": self.allocated_total_replay_seeds,
            "executed_replays": self.executed_replays,
            "scenarios_with_reachable_targets": self.scenarios_with_reachable_targets,
            "scenarios_without_reachable_targets": self.scenarios_without_reachable_targets,
            "target_single_scenarios": self.target_single_scenarios,
            "target_spread_scenarios": self.target_spread_scenarios,
            "no_boundary_scenarios": self.no_boundary_scenarios,
            "disabled_scenarios": self.disabled_scenarios,
            "reduced_allocation_scenarios": self.reduced_allocation_scenarios,
            "redistributed_scenarios": self.redistributed_scenarios,
            "frontier_capped_scenarios": self.frontier_capped_scenarios,
            "multi_target_priority_scenarios": self.multi_target_priority_scenarios,
            "kind_diverse_priority_scenarios": self.kind_diverse_priority_scenarios,
            "unique_selected_targets": list(self.unique_selected_targets),
            "unique_planned_fault_kinds": list(self.unique_planned_fault_kinds),
            "kind_diverse_scenarios": self.kind_diverse_scenarios,
        }


@dataclass(slots=True)
class InvariantView:
    name: str
    source: str
    status: str
    type: str
    review_state: str | None
    review_reason: str | None
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
            review_state=(
                invariant.review.state.value
                if invariant.review is not None
                else ("pending" if invariant.is_pending_suggestion() else None)
            ),
            review_reason=None if invariant.review is None else invariant.review.reason,
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
        if self.review_state is not None:
            payload["review_state"] = self.review_state
        if self.review_reason is not None:
            payload["review_reason"] = self.review_reason
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
    performance: PerformanceCounts
    boundary_coverage: dict[str, BoundaryCoverageCounts] = field(default_factory=dict)
    compatibility: CompatibilityReport = field(
        default_factory=lambda: CompatibilityReport.from_dict({})
    )
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
            "performance": self.performance.to_dict(),
            "boundary_coverage": {
                boundary: coverage.to_dict()
                for boundary, coverage in self.boundary_coverage.items()
            },
            "compatibility": self.compatibility.to_dict(),
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
    pending_review: int


class ReplayCountsPayload(BaseModel):
    unchanged: int
    breaking: int
    benign: int
    improvement: int


class PropertyCountsPayload(BaseModel):
    passed: int
    failed: int
    skipped: int


class PerformancePayload(BaseModel):
    mode: str
    fault_profile: str
    budget_policy: str
    search_strategy: str
    measured: bool
    elapsed_ms: int | None = None
    budget_ms: int
    within_budget: bool | None = None
    replay_seeds_per_scenario: int
    property_max_examples: int
    search_budget: SearchBudgetPayload


class SearchBudgetPayload(BaseModel):
    requested_seeds_per_scenario: int
    requested_total_replay_seeds: int
    allocated_total_replay_seeds: int
    executed_replays: int
    scenarios_with_reachable_targets: int
    scenarios_without_reachable_targets: int
    target_single_scenarios: int
    target_spread_scenarios: int
    no_boundary_scenarios: int
    disabled_scenarios: int
    reduced_allocation_scenarios: int
    redistributed_scenarios: int
    frontier_capped_scenarios: int
    multi_target_priority_scenarios: int
    kind_diverse_priority_scenarios: int
    unique_selected_targets: list[str]
    unique_planned_fault_kinds: list[str]
    kind_diverse_scenarios: int


class BoundaryCoveragePayload(BaseModel):
    detected: bool
    intercepted: bool
    simulated: bool
    faulted: bool
    unsupported: bool


class CompatibilityMatrixEntryPayload(BaseModel):
    package: str
    supported_shapes: list[str]


class CompatibilityMatrixPayload(BaseModel):
    python: str
    asgi: str
    http: CompatibilityMatrixEntryPayload
    sqlalchemy: CompatibilityMatrixEntryPayload
    redis: CompatibilityMatrixEntryPayload


class CompatibilityBoundaryPayload(BaseModel):
    status: str
    detected: bool
    intercepted: bool
    simulated: bool
    faulted: bool
    unsupported: bool
    supported_shapes: list[str]
    unsupported_details: list[str]


class CompatibilityBoundariesPayload(BaseModel):
    http: CompatibilityBoundaryPayload
    sqlalchemy: CompatibilityBoundaryPayload
    redis: CompatibilityBoundaryPayload


class CompatibilityPayload(BaseModel):
    matrix: CompatibilityMatrixPayload
    boundaries: CompatibilityBoundariesPayload


class InvariantViewPayload(BaseModel):
    name: str
    source: str
    status: str
    type: str
    review_state: str | None = None
    review_reason: str | None = None
    reasoning: str | None = None
    method: str | None = None
    path: str | None = None


class ReplayResponsePayload(BaseModel):
    status_code: int | None
    body: object | None


class ReplayFaultContextPayload(BaseModel):
    selected_faults: list[str] = []
    injected_faults: list[str] = []
    boundary_coverage: list[str] = []
    defaulted_responses: list[str] = []
    app_exception: str | None = None


class ReplayCheckpointPayload(BaseModel):
    kind: str
    target: str | None = None
    detail: str | None = None
    status_code: int | None = None


class SchedulerDecisionPayload(BaseModel):
    kind: str
    step: int | None = None
    target: str | None = None
    detail: str | None = None
    params: dict[str, object] = {}


class ReplayFidelityPayload(BaseModel):
    status: str
    drift_kind: str | None = None
    recorded_step: int | None = None
    replay_step: int | None = None
    reason: str
    recorded_decision: SchedulerDecisionPayload | None = None
    replay_decision: SchedulerDecisionPayload | None = None
    recorded_checkpoint: ReplayCheckpointPayload | None = None
    replay_checkpoint: ReplayCheckpointPayload | None = None


class ReplayExplanationPayload(BaseModel):
    seed: str
    method: str
    path: str
    classification: str
    baseline: ReplayResponsePayload
    current: ReplayResponsePayload
    reasons: list[str]
    fault_context: ReplayFaultContextPayload
    fidelity: ReplayFidelityPayload
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
    performance: PerformancePayload
    boundary_coverage: dict[str, BoundaryCoveragePayload]
    compatibility: CompatibilityPayload
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
