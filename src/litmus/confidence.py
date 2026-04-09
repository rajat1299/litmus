from __future__ import annotations

from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification


def calculate_confidence_score(
    replay_results,
    property_results,
) -> float:
    successful_replays = sum(
        1
        for result in replay_results
        if result.classification is not ReplayClassification.BREAKING_CHANGE
    )
    scored_properties = [
        result
        for result in property_results
        if result.status is not PropertyCheckStatus.SKIPPED
    ]
    successful_properties = sum(
        1
        for result in scored_properties
        if result.status is PropertyCheckStatus.PASSED
    )

    total_signals = len(replay_results) + len(scored_properties)
    if total_signals == 0:
        return 0.0

    return (successful_replays + successful_properties) / total_signals
