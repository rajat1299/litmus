from __future__ import annotations

from pathlib import Path

from litmus.invariants.mined import mine_invariants_from_tests
from litmus.invariants.models import InvariantStatus, InvariantType


def test_mine_invariants_from_pytest_style_payment_tests() -> None:
    fixture_file = Path(__file__).resolve().parents[2] / "fixtures" / "tests" / "test_payment.py"

    invariants = mine_invariants_from_tests([fixture_file])

    assert [invariant.name for invariant in invariants] == [
        "charge_returns_200_on_success",
        "charge_returns_402_on_insufficient_funds",
    ]
    assert all(invariant.status is InvariantStatus.CONFIRMED for invariant in invariants)
    assert all(invariant.type is InvariantType.DIFFERENTIAL for invariant in invariants)
    assert invariants[0].request.path == "/payments/charge"
    assert invariants[0].response.status_code == 200
    assert invariants[1].response.status_code == 402


def test_mine_invariants_skips_tests_without_supported_request_response_pattern(
    tmp_path: Path,
) -> None:
    fixture_file = tmp_path / "test_helper.py"
    fixture_file.write_text(
        """
def test_helper_case():
    assert 1 == 1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    invariants = mine_invariants_from_tests([fixture_file])

    assert invariants == []


def test_mine_invariants_from_async_pytest_style_payment_tests(tmp_path: Path) -> None:
    fixture_file = tmp_path / "test_async_payment.py"
    fixture_file.write_text(
        """
async def test_async_charge():
    request = {
        "method": "POST",
        "path": "/payments/charge",
        "json": {"amount": 100},
    }
    response = {
        "status_code": 200,
        "json": {"status": "charged"},
    }

    assert response["status_code"] == 200
""".strip()
        + "\n",
        encoding="utf-8",
    )

    invariants = mine_invariants_from_tests([fixture_file])

    assert [invariant.name for invariant in invariants] == ["async_charge"]
    assert invariants[0].request.path == "/payments/charge"
    assert invariants[0].response.status_code == 200
