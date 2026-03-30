from __future__ import annotations

from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)


def test_invariant_model_preserves_confirmed_and_suggested_statuses() -> None:
    confirmed = Invariant(
        name="charge_returns_200_on_success",
        source="mined:test_payment.py::test_charge_returns_200_on_success",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/charge"),
        response=ResponseExample(status_code=200),
    )
    suggested = Invariant(
        name="charge_is_idempotent_on_retry",
        source="llm:diff_analysis",
        status=InvariantStatus.SUGGESTED,
        type=InvariantType.PROPERTY,
    )

    assert confirmed.status is InvariantStatus.CONFIRMED
    assert suggested.status is InvariantStatus.SUGGESTED
    assert confirmed.request.path == "/payments/charge"
    assert confirmed.response.status_code == 200
