from __future__ import annotations

from collections import Counter

from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.reporting.confidence import calculate_confidence_score


def render_verification_summary(result) -> str:
    replay_counts = Counter(replay.classification for replay in result.replay_results)
    property_counts = Counter(property_result.status for property_result in result.property_results)
    confidence = calculate_confidence_score(result.replay_results, result.property_results)

    return "\n".join(
        [
            "Litmus verify",
            f"App: {result.app_reference}",
            f"Routes: {len(result.routes)}",
            f"Invariants: {len(result.invariants)}",
            f"Scenarios: {len(result.scenarios)}",
            "Replay: "
            f"unchanged={replay_counts[ReplayClassification.UNCHANGED]} "
            f"breaking={replay_counts[ReplayClassification.BREAKING_CHANGE]} "
            f"benign={replay_counts[ReplayClassification.BENIGN_CHANGE]} "
            f"improvement={replay_counts[ReplayClassification.IMPROVEMENT]}",
            "Properties: "
            f"passed={property_counts[PropertyCheckStatus.PASSED]} "
            f"failed={property_counts[PropertyCheckStatus.FAILED]} "
            f"skipped={property_counts[PropertyCheckStatus.SKIPPED]}",
            f"Confidence: {confidence:.2f}",
        ]
    )
