from __future__ import annotations

from pathlib import Path

import pytest

from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
)
from litmus.invariants.store import load_invariants, save_invariants
from litmus.management import accept_invariant, dismiss_invariant
from litmus.runs.store import runs_root


def test_accept_invariant_does_not_persist_review_run_when_invariant_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    save_invariants(
        invariants_path,
        [
            Invariant(
                name="charge_is_idempotent_on_retry",
                source="manual:suggested",
                status=InvariantStatus.SUGGESTED,
                type=InvariantType.PROPERTY,
                request=RequestExample(method="POST", path="/payments/charge"),
                reasoning="Review retry behavior before trusting this endpoint.",
            )
        ],
    )

    monkeypatch.setattr("litmus.management.save_invariants", _raise_disk_full)

    with pytest.raises(OSError, match="disk full"):
        accept_invariant(tmp_path, name="charge_is_idempotent_on_retry", reason="Looks good.")

    invariants = load_invariants(invariants_path)
    assert invariants[0].status is InvariantStatus.SUGGESTED
    assert invariants[0].review is None
    assert not runs_root(tmp_path).exists()


def test_dismiss_invariant_does_not_persist_review_run_when_invariant_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    save_invariants(
        invariants_path,
        [
            Invariant(
                name="charge_is_idempotent_on_retry",
                source="manual:suggested",
                status=InvariantStatus.SUGGESTED,
                type=InvariantType.PROPERTY,
                request=RequestExample(method="POST", path="/payments/charge"),
                reasoning="Review retry behavior before trusting this endpoint.",
            )
        ],
    )

    monkeypatch.setattr("litmus.management.save_invariants", _raise_disk_full)

    with pytest.raises(OSError, match="disk full"):
        dismiss_invariant(
            tmp_path,
            name="charge_is_idempotent_on_retry",
            reason="Retry behavior is already enforced elsewhere.",
        )

    invariants = load_invariants(invariants_path)
    assert invariants[0].status is InvariantStatus.SUGGESTED
    assert invariants[0].review is None
    assert not runs_root(tmp_path).exists()


def test_accept_invariant_does_not_update_curated_store_when_review_manifest_persist_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    save_invariants(invariants_path, [_suggested_invariant()])

    monkeypatch.setattr("litmus.management.persist_invariant_review_run", _raise_disk_full)

    with pytest.raises(OSError, match="disk full"):
        accept_invariant(tmp_path, name="charge_is_idempotent_on_retry", reason="Looks good.")

    invariants = load_invariants(invariants_path)
    assert invariants[0].status is InvariantStatus.SUGGESTED
    assert invariants[0].review is None
    assert not runs_root(tmp_path).exists()


def test_accept_invariant_rolls_back_curated_store_when_invariant_write_raises_after_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    save_invariants(invariants_path, [_suggested_invariant()])

    monkeypatch.setattr("litmus.management.save_invariants", _write_then_raise)

    with pytest.raises(OSError, match="disk full after write"):
        accept_invariant(tmp_path, name="charge_is_idempotent_on_retry", reason="Looks good.")

    invariants = load_invariants(invariants_path)
    assert invariants[0].status is InvariantStatus.SUGGESTED
    assert invariants[0].review is None
    assert not runs_root(tmp_path).exists()


def test_dismiss_invariant_does_not_update_curated_store_when_review_manifest_persist_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    save_invariants(invariants_path, [_suggested_invariant()])

    monkeypatch.setattr("litmus.management.persist_invariant_review_run", _raise_disk_full)

    with pytest.raises(OSError, match="disk full"):
        dismiss_invariant(
            tmp_path,
            name="charge_is_idempotent_on_retry",
            reason="Retry behavior is already enforced elsewhere.",
        )

    invariants = load_invariants(invariants_path)
    assert invariants[0].status is InvariantStatus.SUGGESTED
    assert invariants[0].review is None
    assert not runs_root(tmp_path).exists()


def test_dismiss_invariant_rolls_back_curated_store_when_invariant_write_raises_after_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    save_invariants(invariants_path, [_suggested_invariant()])

    monkeypatch.setattr("litmus.management.save_invariants", _write_then_raise)

    with pytest.raises(OSError, match="disk full after write"):
        dismiss_invariant(
            tmp_path,
            name="charge_is_idempotent_on_retry",
            reason="Retry behavior is already enforced elsewhere.",
        )

    invariants = load_invariants(invariants_path)
    assert invariants[0].status is InvariantStatus.SUGGESTED
    assert invariants[0].review is None
    assert not runs_root(tmp_path).exists()


def _suggested_invariant() -> Invariant:
    return Invariant(
        name="charge_is_idempotent_on_retry",
        source="manual:suggested",
        status=InvariantStatus.SUGGESTED,
        type=InvariantType.PROPERTY,
        request=RequestExample(method="POST", path="/payments/charge"),
        reasoning="Review retry behavior before trusting this endpoint.",
    )


def _raise_disk_full(*_args, **_kwargs) -> None:
    raise OSError("disk full")


def _write_then_raise(*args, **kwargs) -> None:
    save_invariants(*args, **kwargs)
    raise OSError("disk full after write")
