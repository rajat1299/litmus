from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from litmus.compatibility import compatibility_report_from_result
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification


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
    confidence: float

    @classmethod
    def from_result(cls, result) -> VerificationProjection:
        from litmus.reporting.confidence import calculate_confidence_score

        replay_counts = Counter(replay.classification.value for replay in result.replay_results)
        property_counts = Counter(property_result.status.value for property_result in result.property_results)
        confirmed_invariants = sum(1 for invariant in result.invariants if invariant.status.value == "confirmed")
        suggested_invariants = sum(1 for invariant in result.invariants if invariant.status.value == "suggested")
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
            "confidence": self.confidence,
        }


def summarize_verification_result(result) -> dict[str, Any]:
    return VerificationProjection.from_result(result).to_dict()
