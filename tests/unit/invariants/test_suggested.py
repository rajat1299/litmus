from __future__ import annotations

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)
from litmus.invariants.suggested import (
    HeuristicRouteGapSuggestionProvider,
    SuggestionContext,
    suggest_invariants,
)


class StubSuggestionProvider:
    def __init__(self, invariants: list[Invariant]) -> None:
        self.invariants = invariants
        self.context: SuggestionContext | None = None

    def suggest(self, context: SuggestionContext) -> list[Invariant]:
        self.context = context
        return self.invariants


def test_suggest_invariants_delegates_to_provider_and_normalizes_status() -> None:
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
        )
    ]
    provider = StubSuggestionProvider(
        [
            Invariant(
                name="charge_is_idempotent_on_retry",
                source="llm:diff_analysis",
                status=InvariantStatus.CONFIRMED,
                type=InvariantType.PROPERTY,
                request=RequestExample(
                    method="POST",
                    path="/payments/charge",
                    payload={"amount": 100},
                ),
                reasoning="Retry logic replays the charge call without a dedupe key.",
            )
        ]
    )

    suggestions = suggest_invariants(
        provider=provider,
        changed_files=["src/services/payments.py"],
        endpoints=endpoints,
        existing_invariants=existing,
    )

    assert provider.context is not None
    assert provider.context.changed_files == ["src/services/payments.py"]
    assert provider.context.endpoints == endpoints
    assert [invariant.name for invariant in provider.context.existing_invariants] == [
        "charge_returns_200_on_success"
    ]
    assert [invariant.name for invariant in suggestions] == ["charge_is_idempotent_on_retry"]
    assert suggestions[0].status is InvariantStatus.SUGGESTED
    assert suggestions[0].reasoning == "Retry logic replays the charge call without a dedupe key."


def test_heuristic_provider_suggests_only_selected_endpoints_without_confirmed_anchor() -> None:
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

    suggestions = suggest_invariants(
        provider=HeuristicRouteGapSuggestionProvider(),
        changed_files=[],
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
