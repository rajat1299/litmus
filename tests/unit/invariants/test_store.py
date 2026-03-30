from __future__ import annotations

from pathlib import Path

from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)
from litmus.invariants.store import load_invariants, save_invariants


def test_save_and_load_invariants_round_trip_yaml(tmp_path: Path) -> None:
    invariants = [
        Invariant(
            name="charge_returns_200_on_success",
            source="mined:test_payment.py::test_charge_returns_200_on_success",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/charge"),
            response=ResponseExample(status_code=200),
        ),
        Invariant(
            name="charge_is_idempotent_on_retry",
            source="llm:diff_analysis",
            status=InvariantStatus.SUGGESTED,
            type=InvariantType.PROPERTY,
        ),
    ]
    output_file = tmp_path / "payment_service.yaml"

    save_invariants(output_file, invariants)
    loaded = load_invariants(output_file)

    assert [invariant.name for invariant in loaded] == [
        "charge_returns_200_on_success",
        "charge_is_idempotent_on_retry",
    ]
    assert loaded[0].status is InvariantStatus.CONFIRMED
    assert loaded[1].status is InvariantStatus.SUGGESTED
    assert loaded[0].response.status_code == 200
