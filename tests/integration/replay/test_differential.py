from __future__ import annotations

import asyncio

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import Invariant, InvariantStatus, InvariantType
from litmus.invariants.models import RequestExample, ResponseExample
from litmus.replay.differential import ReplayClassification, run_differential_replay
from litmus.scenarios.builder import build_scenarios
from litmus.scenarios.builder import Scenario


def test_run_differential_replay_skips_scenarios_without_baseline_response() -> None:
    calls: list[Scenario] = []
    scenarios = [
        Scenario(
            method="POST",
            path="/payments/charge",
            request=RequestExample(method="POST", path="/payments/charge", payload={"amount": 100}),
            expected_response=None,
        )
    ]

    async def runner(scenario: Scenario) -> ResponseExample:
        calls.append(scenario)
        return ResponseExample(status_code=200)

    results = asyncio.run(run_differential_replay(scenarios=scenarios, runner=runner))

    assert results == []
    assert calls == []


def test_run_differential_replay_skips_suggested_only_scenarios_from_builder() -> None:
    calls: list[Scenario] = []
    routes = [
        RouteDefinition(
            method="POST",
            path="/payments/charge",
            handler_name="charge",
            file_path="service/api.py",
        )
    ]
    invariants = [
        Invariant(
            name="charge_accepts_async_processing",
            source="llm:diff_analysis",
            status=InvariantStatus.SUGGESTED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(
                method="POST",
                path="/payments/charge",
                payload={"amount": 100},
            ),
            response=ResponseExample(status_code=202),
        )
    ]
    scenarios = build_scenarios(routes=routes, invariants=invariants)

    async def runner(scenario: Scenario) -> ResponseExample:
        calls.append(scenario)
        return ResponseExample(status_code=202)

    results = asyncio.run(run_differential_replay(scenarios=scenarios, runner=runner))

    assert len(scenarios) == 1
    assert results == []
    assert calls == []


def test_run_differential_replay_classifies_unchanged_response() -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", payload={"amount": 100}),
        expected_response=ResponseExample(status_code=200, body={"status": "charged"}),
    )

    async def runner(_: Scenario) -> ResponseExample:
        return ResponseExample(status_code=200, body={"status": "charged"})

    results = asyncio.run(run_differential_replay(scenarios=[scenario], runner=runner))

    assert len(results) == 1
    assert results[0].classification is ReplayClassification.UNCHANGED
    assert results[0].diff == {}


def test_run_differential_replay_classifies_breaking_change() -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", payload={"amount": 100}),
        expected_response=ResponseExample(status_code=200, body={"status": "charged"}),
    )

    async def runner(_: Scenario) -> ResponseExample:
        return ResponseExample(status_code=500, body={"error": "timeout"})

    results = asyncio.run(run_differential_replay(scenarios=[scenario], runner=runner))

    assert len(results) == 1
    assert results[0].classification is ReplayClassification.BREAKING_CHANGE
    assert results[0].diff == {
        "status_code": (200, 500),
        "body": ({"status": "charged"}, {"error": "timeout"}),
    }


def test_run_differential_replay_classifies_benign_change() -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", payload={"amount": 100}),
        expected_response=ResponseExample(status_code=200, body={"status": "charged"}),
    )

    async def runner(_: Scenario) -> ResponseExample:
        return ResponseExample(status_code=200, body={"status": "charged", "id": "txn_123"})

    results = asyncio.run(run_differential_replay(scenarios=[scenario], runner=runner))

    assert len(results) == 1
    assert results[0].classification is ReplayClassification.BENIGN_CHANGE
    assert results[0].diff == {
        "body": ({"status": "charged"}, {"status": "charged", "id": "txn_123"}),
    }


def test_run_differential_replay_classifies_improvement() -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", payload={"amount": 100}),
        expected_response=ResponseExample(status_code=500, body={"error": "timeout"}),
    )

    async def runner(_: Scenario) -> ResponseExample:
        return ResponseExample(status_code=200, body={"status": "charged"})

    results = asyncio.run(run_differential_replay(scenarios=[scenario], runner=runner))

    assert len(results) == 1
    assert results[0].classification is ReplayClassification.IMPROVEMENT
    assert results[0].diff == {
        "status_code": (500, 200),
        "body": ({"error": "timeout"}, {"status": "charged"}),
    }
