from __future__ import annotations

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)
from litmus.invariants.suggested import suggest_route_gap_invariants


def test_suggest_route_gap_invariants_suggests_only_selected_endpoints_without_confirmed_anchor() -> None:
    existing = [
        Invariant(
            name="charge_returns_200_on_success",
            source="mined:tests/test_payment.py::test_charge_success",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/charge"),
            response=ResponseExample(status_code=200),
        )
    ]
    endpoints = [
        RouteDefinition(
            method="POST",
            path="/payments/charge",
            handler_name="charge",
            file_path="service/api.py",
        ),
        RouteDefinition(
            method="POST",
            path="/payments/refund",
            handler_name="refund",
            file_path="service/api.py",
        ),
    ]

    suggestions = suggest_route_gap_invariants(
        endpoints=endpoints,
        existing_invariants=existing,
    )

    assert [suggestion.name for suggestion in suggestions] == [
        "refund_post_payments_refund_needs_confirmed_anchor"
    ]
    assert suggestions[0].source == "suggested:route_gap"
    assert suggestions[0].status is InvariantStatus.SUGGESTED
    assert suggestions[0].request is not None
    assert suggestions[0].request.method == "POST"
    assert suggestions[0].request.path == "/payments/refund"
    assert suggestions[0].reasoning == (
        "POST /payments/refund is selected for verification without a confirmed mined invariant anchor. "
        "Add or approve a baseline before trusting verification coverage."
    )


def test_suggest_route_gap_invariants_skips_routes_with_existing_suggested_entries() -> None:
    existing = [
        Invariant(
            name="refund_needs_review",
            source="manual:suggested",
            status=InvariantStatus.SUGGESTED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/refund"),
        )
    ]
    endpoints = [
        RouteDefinition(
            method="POST",
            path="/payments/refund",
            handler_name="refund",
            file_path="service/api.py",
        )
    ]

    suggestions = suggest_route_gap_invariants(
        endpoints=endpoints,
        existing_invariants=existing,
    )

    assert suggestions == []
