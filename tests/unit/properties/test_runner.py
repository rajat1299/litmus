from __future__ import annotations

from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
)
from litmus.properties.runner import PropertyCheckStatus, run_property_checks


def test_run_property_checks_passes_confirmed_property_invariant() -> None:
    invariant = Invariant(
        name="charge_amount_is_integer",
        source="mined:tests/test_payment.py::test_charge_amount_is_integer",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.PROPERTY,
        request=RequestExample(
            method="POST",
            path="/payments/charge",
            payload={"amount": 1},
        ),
    )

    def checker(_: Invariant, request: RequestExample) -> bool:
        return (
            request.method == "POST"
            and request.path == "/payments/charge"
            and isinstance(request.payload["amount"], int)
        )

    results = run_property_checks([invariant], checker, max_examples=20)

    assert len(results) == 1
    assert results[0].status is PropertyCheckStatus.PASSED
    assert results[0].failing_request is None
    assert results[0].reason is None


def test_run_property_checks_returns_shrunk_counterexample_for_failure() -> None:
    invariant = Invariant(
        name="charge_amount_stays_below_five",
        source="mined:tests/test_payment.py::test_charge_amount_stays_below_five",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.PROPERTY,
        request=RequestExample(
            method="POST",
            path="/payments/charge",
            payload={"amount": 4},
        ),
    )

    def checker(_: Invariant, request: RequestExample) -> bool:
        return request.payload["amount"] < 5

    results = run_property_checks([invariant], checker, max_examples=25)

    assert len(results) == 1
    assert results[0].status is PropertyCheckStatus.FAILED
    assert results[0].failing_request is not None
    assert results[0].failing_request.payload == {"amount": 5}


def test_run_property_checks_skips_suggested_property_invariants() -> None:
    calls: list[RequestExample] = []
    invariant = Invariant(
        name="charge_is_idempotent_on_retry",
        source="llm:diff_analysis",
        status=InvariantStatus.SUGGESTED,
        type=InvariantType.PROPERTY,
        request=RequestExample(
            method="POST",
            path="/payments/charge",
            payload={"amount": 1},
        ),
    )

    def checker(_: Invariant, request: RequestExample) -> bool:
        calls.append(request)
        return True

    results = run_property_checks([invariant], checker, max_examples=20)

    assert len(results) == 1
    assert results[0].status is PropertyCheckStatus.SKIPPED
    assert results[0].reason == "only confirmed invariants can run as property checks"
    assert calls == []


def test_run_property_checks_skips_non_property_invariants() -> None:
    calls: list[RequestExample] = []
    invariant = Invariant(
        name="charge_returns_200_on_success",
        source="mined:tests/test_payment.py::test_charge_success",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(
            method="POST",
            path="/payments/charge",
            payload={"amount": 1},
        ),
    )

    def checker(_: Invariant, request: RequestExample) -> bool:
        calls.append(request)
        return True

    results = run_property_checks([invariant], checker, max_examples=20)

    assert len(results) == 1
    assert results[0].status is PropertyCheckStatus.SKIPPED
    assert results[0].reason == "only property invariants can run in the property layer"
    assert calls == []
