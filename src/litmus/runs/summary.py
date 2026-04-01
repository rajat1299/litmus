from __future__ import annotations

from collections import Counter
from typing import Any

from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.reporting.confidence import calculate_confidence_score


def summarize_verification_result(result) -> dict[str, Any]:
    replay_counts = Counter(replay.classification.value for replay in result.replay_results)
    property_counts = Counter(property_result.status.value for property_result in result.property_results)
    return {
        "routes": len(result.routes),
        "invariants": len(result.invariants),
        "scenarios": len(result.scenarios),
        "replay": {
            ReplayClassification.UNCHANGED.value: replay_counts[ReplayClassification.UNCHANGED.value],
            ReplayClassification.BREAKING_CHANGE.value: replay_counts[ReplayClassification.BREAKING_CHANGE.value],
            ReplayClassification.BENIGN_CHANGE.value: replay_counts[ReplayClassification.BENIGN_CHANGE.value],
            ReplayClassification.IMPROVEMENT.value: replay_counts[ReplayClassification.IMPROVEMENT.value],
        },
        "properties": {
            PropertyCheckStatus.PASSED.value: property_counts[PropertyCheckStatus.PASSED.value],
            PropertyCheckStatus.FAILED.value: property_counts[PropertyCheckStatus.FAILED.value],
            PropertyCheckStatus.SKIPPED.value: property_counts[PropertyCheckStatus.SKIPPED.value],
        },
        "confidence": calculate_confidence_score(result.replay_results, result.property_results),
    }
