from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from litmus.invariants.models import InvariantStatus, ResponseExample
from litmus.scenarios.builder import Scenario


class ReplayClassification(str, Enum):
    UNCHANGED = "unchanged"
    BREAKING_CHANGE = "breaking_change"
    BENIGN_CHANGE = "benign_change"
    IMPROVEMENT = "improvement"


@dataclass(slots=True)
class DifferentialReplayResult:
    scenario: Scenario
    baseline_response: ResponseExample
    changed_response: ResponseExample
    classification: ReplayClassification
    diff: dict[str, tuple[Any, Any]] = field(default_factory=dict)


ReplayRunner = Callable[[Scenario], Awaitable[ResponseExample]]


async def run_differential_replay(
    scenarios: list[Scenario],
    runner: ReplayRunner,
) -> list[DifferentialReplayResult]:
    results: list[DifferentialReplayResult] = []

    for scenario in scenarios:
        baseline_response = _baseline_response_for_replay(scenario)
        if baseline_response is None:
            continue

        changed_response = await runner(scenario)
        diff = _response_diff(baseline_response, changed_response)
        classification = _classify_replay(baseline_response, changed_response, diff)
        results.append(
            DifferentialReplayResult(
                scenario=scenario,
                baseline_response=baseline_response,
                changed_response=changed_response,
                classification=classification,
                diff=diff,
            )
        )

    return results


def _baseline_response_for_replay(scenario: Scenario) -> ResponseExample | None:
    if not scenario.invariants:
        return scenario.expected_response

    for invariant in scenario.invariants:
        if invariant.status is InvariantStatus.CONFIRMED and invariant.response is not None:
            return invariant.response

    return None


def _response_diff(
    baseline_response: ResponseExample,
    changed_response: ResponseExample,
) -> dict[str, tuple[Any, Any]]:
    diff: dict[str, tuple[Any, Any]] = {}

    if baseline_response.status_code != changed_response.status_code:
        diff["status_code"] = (baseline_response.status_code, changed_response.status_code)

    if baseline_response.body != changed_response.body:
        diff["body"] = (baseline_response.body, changed_response.body)

    return diff


def _classify_replay(
    baseline_response: ResponseExample,
    changed_response: ResponseExample,
    diff: dict[str, tuple[Any, Any]],
) -> ReplayClassification:
    if not diff:
        return ReplayClassification.UNCHANGED

    baseline_rank = _status_rank(baseline_response.status_code)
    changed_rank = _status_rank(changed_response.status_code)

    if changed_rank > baseline_rank:
        return ReplayClassification.IMPROVEMENT

    if changed_rank < baseline_rank:
        return ReplayClassification.BREAKING_CHANGE

    return ReplayClassification.BENIGN_CHANGE


def _status_rank(status_code: int | None) -> int:
    if status_code is None:
        return -1
    if 200 <= status_code < 300:
        return 3
    if 300 <= status_code < 400:
        return 2
    if 400 <= status_code < 500:
        return 1
    if 500 <= status_code < 600:
        return 0
    return -1
