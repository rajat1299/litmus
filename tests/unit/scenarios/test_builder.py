from __future__ import annotations

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)
from litmus.scenarios.builder import build_scenarios


def test_build_scenarios_combines_confirmed_and_suggested_invariants_for_same_request() -> None:
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
            name="charge_returns_200_on_success",
            source="mined:tests/test_payment.py::test_charge_success",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(
                method="POST",
                path="/payments/charge",
                payload={"amount": 100},
            ),
            response=ResponseExample(status_code=200),
        ),
        Invariant(
            name="charge_is_idempotent_on_retry",
            source="llm:diff_analysis",
            status=InvariantStatus.SUGGESTED,
            type=InvariantType.PROPERTY,
            request=RequestExample(
                method="POST",
                path="/payments/charge",
                payload={"amount": 100},
            ),
            reasoning="Retries should not create a duplicate charge.",
        ),
        Invariant(
            name="health_endpoint_stays_up",
            source="mined:tests/test_health.py::test_health_ok",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="GET", path="/health"),
            response=ResponseExample(status_code=200),
        ),
    ]

    scenarios = build_scenarios(routes=routes, invariants=invariants)

    assert len(scenarios) == 1
    assert scenarios[0].method == "POST"
    assert scenarios[0].path == "/payments/charge"
    assert scenarios[0].request.payload == {"amount": 100}
    assert scenarios[0].expected_response.status_code == 200
    assert [invariant.name for invariant in scenarios[0].invariants] == [
        "charge_returns_200_on_success",
        "charge_is_idempotent_on_retry",
    ]


def test_build_scenarios_keeps_distinct_requests_separate_on_same_endpoint() -> None:
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
            name="charge_returns_200_on_success",
            source="mined:tests/test_payment.py::test_charge_success",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(
                method="POST",
                path="/payments/charge",
                payload={"amount": 100},
            ),
            response=ResponseExample(status_code=200),
        ),
        Invariant(
            name="charge_returns_402_on_insufficient_funds",
            source="mined:tests/test_payment.py::test_charge_nsf",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(
                method="POST",
                path="/payments/charge",
                payload={"amount": 10_000},
            ),
            response=ResponseExample(status_code=402),
        ),
    ]

    scenarios = build_scenarios(routes=routes, invariants=invariants)

    assert len(scenarios) == 2
    assert [scenario.request.payload for scenario in scenarios] == [
        {"amount": 100},
        {"amount": 10_000},
    ]
    assert [scenario.expected_response.status_code for scenario in scenarios] == [200, 402]


def test_build_scenarios_prefers_confirmed_response_over_suggested_response_for_same_request() -> None:
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
        ),
        Invariant(
            name="charge_returns_200_on_success",
            source="mined:tests/test_payment.py::test_charge_success",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(
                method="POST",
                path="/payments/charge",
                payload={"amount": 100},
            ),
            response=ResponseExample(status_code=200),
        ),
    ]

    scenarios = build_scenarios(routes=routes, invariants=invariants)

    assert len(scenarios) == 1
    assert scenarios[0].expected_response is not None
    assert scenarios[0].expected_response.status_code == 200
