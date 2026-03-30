from __future__ import annotations

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)
from litmus.invariants.suggested import SuggestionContext, suggest_invariants


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
