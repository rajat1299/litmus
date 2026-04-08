from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from litmus.compatibility import compatibility_report_from_result
from litmus.performance import (
    budget_policy_for_mode,
    coerce_fault_profile,
    coerce_run_mode,
    elapsed_ms,
    property_max_examples_for_mode,
    replay_seed_count_for_mode,
    verify_budget_ms_for_mode,
)
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.search_budget import summarize_search_budget


@dataclass(slots=True)
class PerformanceProjection:
    mode: str
    fault_profile: str
    budget_policy: str
    measured: bool
    elapsed_ms: int | None
    budget_ms: int
    within_budget: bool | None
    replay_seeds_per_scenario: int
    property_max_examples: int
    search_budget: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "fault_profile": self.fault_profile,
            "budget_policy": self.budget_policy,
            "measured": self.measured,
            "elapsed_ms": self.elapsed_ms,
            "budget_ms": self.budget_ms,
            "within_budget": self.within_budget,
            "replay_seeds_per_scenario": self.replay_seeds_per_scenario,
            "property_max_examples": self.property_max_examples,
            "search_budget": dict(self.search_budget),
        }


@dataclass(slots=True)
class VerificationProjection:
    app_reference: str
    scope_label: str
    routes: int
    invariants: dict[str, int]
    scenarios: int
    replay: dict[str, int]
    properties: dict[str, int]
    compatibility: dict[str, Any]
    performance: dict[str, Any]
    confidence: float

    @classmethod
    def from_result(cls, result) -> VerificationProjection:
        from litmus.reporting.confidence import calculate_confidence_score

        replay_counts = Counter(replay.classification.value for replay in result.replay_results)
        property_counts = Counter(property_result.status.value for property_result in result.property_results)
        confirmed_invariants = sum(1 for invariant in result.invariants if invariant.status.value == "confirmed")
        suggested_invariants = sum(1 for invariant in result.invariants if invariant.status.value == "suggested")
        performance = performance_projection_from_result(result)
        return cls(
            app_reference=result.app_reference,
            scope_label=result.scope_label,
            routes=len(result.routes),
            invariants={
                "total": len(result.invariants),
                "confirmed": confirmed_invariants,
                "suggested": suggested_invariants,
            },
            scenarios=len(result.scenarios),
            replay={
                ReplayClassification.UNCHANGED.value: replay_counts[ReplayClassification.UNCHANGED.value],
                ReplayClassification.BREAKING_CHANGE.value: replay_counts[ReplayClassification.BREAKING_CHANGE.value],
                ReplayClassification.BENIGN_CHANGE.value: replay_counts[ReplayClassification.BENIGN_CHANGE.value],
                ReplayClassification.IMPROVEMENT.value: replay_counts[ReplayClassification.IMPROVEMENT.value],
            },
            properties={
                PropertyCheckStatus.PASSED.value: property_counts[PropertyCheckStatus.PASSED.value],
                PropertyCheckStatus.FAILED.value: property_counts[PropertyCheckStatus.FAILED.value],
                PropertyCheckStatus.SKIPPED.value: property_counts[PropertyCheckStatus.SKIPPED.value],
            },
            compatibility=compatibility_report_from_result(result).to_dict(),
            performance=performance.to_dict(),
            confidence=calculate_confidence_score(result.replay_results, result.property_results),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "routes": self.routes,
            "invariants": dict(self.invariants),
            "scenarios": self.scenarios,
            "replay": dict(self.replay),
            "properties": dict(self.properties),
            "compatibility": dict(self.compatibility),
            "performance": dict(self.performance),
            "confidence": self.confidence,
        }


def performance_projection_from_result(result) -> PerformanceProjection:
    mode = coerce_run_mode(getattr(result, "mode", "local"))
    fault_profile = coerce_fault_profile(getattr(result, "fault_profile", "default"))
    replay_seeds_per_scenario = getattr(result, "replay_seeds_per_scenario", None)
    if replay_seeds_per_scenario is None:
        replay_seeds_per_scenario = replay_seed_count_for_mode(mode, fault_profile=fault_profile)
    property_max_examples = getattr(result, "property_max_examples", None)
    if property_max_examples is None:
        property_max_examples = property_max_examples_for_mode(mode, fault_profile=fault_profile)
    duration_ms = elapsed_ms(
        getattr(result, "started_at", None),
        getattr(result, "completed_at", None),
    )
    budget_ms = verify_budget_ms_for_mode(mode)
    measured = duration_ms is not None
    search_budget = summarize_search_budget(
        scenario_count=len(getattr(result, "scenarios", [])),
        requested_seeds_per_scenario=replay_seeds_per_scenario,
        replay_traces=list(getattr(result, "replay_traces", [])),
    )
    return PerformanceProjection(
        mode=mode,
        fault_profile=fault_profile.value,
        budget_policy=budget_policy_for_mode(mode, fault_profile=fault_profile),
        measured=measured,
        elapsed_ms=duration_ms,
        budget_ms=budget_ms,
        within_budget=None if duration_ms is None else duration_ms <= budget_ms,
        replay_seeds_per_scenario=replay_seeds_per_scenario,
        property_max_examples=property_max_examples,
        search_budget=search_budget.to_dict(),
    )


def summarize_verification_result(result) -> dict[str, Any]:
    return VerificationProjection.from_result(result).to_dict()
