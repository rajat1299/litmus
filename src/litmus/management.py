from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from litmus.config import FaultProfile, RepoConfig, load_repo_config, write_repo_config
from litmus.errors import LitmusUserError
from litmus.invariants.models import Invariant, InvariantReview, InvariantReviewState, InvariantStatus
from litmus.invariants.store import default_invariants_path, load_invariants, save_invariants
from litmus.runs import record_invariant_review_run


@dataclass(frozen=True, slots=True)
class InvariantListItem:
    name: str
    status: InvariantStatus
    invariant_type: str
    method: str | None
    path: str | None


@dataclass(frozen=True, slots=True)
class InvariantListResult:
    invariants_path: Path
    invariants: tuple[InvariantListItem, ...]


@dataclass(frozen=True, slots=True)
class InvariantShowResult:
    invariants_path: Path
    invariant: Invariant


@dataclass(frozen=True, slots=True)
class InvariantStatusUpdateResult:
    invariants_path: Path
    invariant: Invariant


@dataclass(frozen=True, slots=True)
class InvariantReviewListItem:
    name: str
    status: InvariantStatus
    review_state: InvariantReviewState
    invariant_type: str
    method: str | None
    path: str | None


@dataclass(frozen=True, slots=True)
class InvariantReviewListResult:
    invariants_path: Path
    filter_name: str
    invariants: tuple[InvariantReviewListItem, ...]


@dataclass(frozen=True, slots=True)
class InvariantReviewUpdateResult:
    invariants_path: Path
    invariant: Invariant


@dataclass(frozen=True, slots=True)
class ConfigSetResult:
    config_path: Path
    key: str
    value: str


def list_invariants(root: Path | str) -> InvariantListResult:
    invariants_path = default_invariants_path(root)
    invariants = [
        invariant
        for invariant in _load_curated_invariants(invariants_path)
        if not invariant.is_dismissed_suggestion()
    ]
    return InvariantListResult(
        invariants_path=invariants_path,
        invariants=tuple(
            InvariantListItem(
                name=invariant.name,
                status=invariant.status,
                invariant_type=invariant.type.value,
                method=invariant.request.method if invariant.request is not None else None,
                path=invariant.request.path if invariant.request is not None else None,
            )
            for invariant in invariants
        ),
    )


def show_invariant(root: Path | str, name: str) -> InvariantShowResult:
    invariants_path = default_invariants_path(root)
    invariant = _find_invariant(_load_curated_invariants(invariants_path), name=name, invariants_path=invariants_path)
    return InvariantShowResult(invariants_path=invariants_path, invariant=invariant)


def list_invariant_reviews(root: Path | str, *, filter_name: str = "pending") -> InvariantReviewListResult:
    invariants_path = default_invariants_path(root)
    invariants = _load_curated_invariants(invariants_path)
    filtered = [invariant for invariant in invariants if _matches_review_filter(invariant, filter_name=filter_name)]
    return InvariantReviewListResult(
        invariants_path=invariants_path,
        filter_name=filter_name,
        invariants=tuple(
            InvariantReviewListItem(
                name=invariant.name,
                status=invariant.status,
                review_state=_review_state_for_listing(invariant),
                invariant_type=invariant.type.value,
                method=invariant.request.method if invariant.request is not None else None,
                path=invariant.request.path if invariant.request is not None else None,
            )
            for invariant in filtered
        ),
    )


def set_invariant_status(
    root: Path | str,
    *,
    name: str,
    status: InvariantStatus,
) -> InvariantStatusUpdateResult:
    invariants_path = default_invariants_path(root)
    invariants = _load_curated_invariants(invariants_path)
    target = _find_invariant(invariants, name=name, invariants_path=invariants_path)
    if status is InvariantStatus.CONFIRMED:
        _ensure_can_confirm(target)
    updated = target.model_copy(
        update={
            "status": status,
            "review": _normalized_review_for_status(target, status=status),
        }
    )
    updated_invariants = [updated if invariant.name == name else invariant for invariant in invariants]
    save_invariants(invariants_path, updated_invariants)
    return InvariantStatusUpdateResult(invariants_path=invariants_path, invariant=updated)


def accept_invariant(root: Path | str, *, name: str, reason: str | None = None) -> InvariantReviewUpdateResult:
    invariants_path = default_invariants_path(root)
    invariants = _load_curated_invariants(invariants_path)
    target = _find_invariant(invariants, name=name, invariants_path=invariants_path)
    if target.status is not InvariantStatus.SUGGESTED:
        raise LitmusUserError(f"Invariant '{name}' is not suggested and cannot be accepted.")
    _ensure_can_confirm(target)
    review_run = record_invariant_review_run(
        root,
        invariant_name=name,
        decision=InvariantReviewState.PROMOTED.value,
        reason=reason,
        review_source="cli",
    )

    updated = target.model_copy(
        update={
            "status": InvariantStatus.CONFIRMED,
            "review": InvariantReview(
                state=InvariantReviewState.PROMOTED,
                reason=reason,
                reviewed_at=_review_timestamp(),
                review_source="cli",
                review_run_id=review_run.run_id,
            ),
        }
    )
    updated_invariants = [updated if invariant.name == name else invariant for invariant in invariants]
    save_invariants(invariants_path, updated_invariants)
    return InvariantReviewUpdateResult(invariants_path=invariants_path, invariant=updated)


def dismiss_invariant(root: Path | str, *, name: str, reason: str) -> InvariantReviewUpdateResult:
    invariants_path = default_invariants_path(root)
    invariants = _load_curated_invariants(invariants_path)
    target = _find_invariant(invariants, name=name, invariants_path=invariants_path)
    if target.status is not InvariantStatus.SUGGESTED:
        raise LitmusUserError(f"Invariant '{name}' is not suggested and cannot be dismissed.")
    review_run = record_invariant_review_run(
        root,
        invariant_name=name,
        decision=InvariantReviewState.DISMISSED.value,
        reason=reason,
        review_source="cli",
    )

    updated = target.model_copy(
        update={
            "review": InvariantReview(
                state=InvariantReviewState.DISMISSED,
                reason=reason,
                reviewed_at=_review_timestamp(),
                review_source="cli",
                review_run_id=review_run.run_id,
            ),
        }
    )
    updated_invariants = [updated if invariant.name == name else invariant for invariant in invariants]
    save_invariants(invariants_path, updated_invariants)
    return InvariantReviewUpdateResult(invariants_path=invariants_path, invariant=updated)


def set_config_value(root: Path | str, *, key: str, value: str) -> ConfigSetResult:
    repo_root = Path(root)
    config_path = repo_root / "litmus.yaml"
    if key == "app":
        overrides = {"app": value}
    elif key == "suggested_invariants":
        overrides = {"suggested_invariants": value}
    elif key == "fault_profile":
        overrides = {"fault_profile": value}
    else:
        raise LitmusUserError(
            "Unsupported config key. Use one of: app, suggested_invariants, fault_profile."
        )

    current = load_repo_config(repo_root, overrides=overrides)

    if key == "app":
        next_config = RepoConfig(
            app=current.app,
            suggested_invariants=current.suggested_invariants,
            fault_profile=current.fault_profile,
        )
        display_value = current.app or value
    elif key == "suggested_invariants":
        next_config = RepoConfig(
            app=current.app,
            suggested_invariants=current.suggested_invariants,
            fault_profile=current.fault_profile,
        )
        display_value = "true" if current.suggested_invariants else "false"
    else:
        next_config = RepoConfig(
            app=current.app,
            suggested_invariants=current.suggested_invariants,
            fault_profile=current.fault_profile,
        )
        display_value = current.fault_profile.value

    write_repo_config(config_path, next_config, include_defaults=True)
    return ConfigSetResult(config_path=config_path, key=key, value=display_value)


def _load_curated_invariants(invariants_path: Path) -> list[Invariant]:
    if not invariants_path.exists():
        return []
    return load_invariants(invariants_path)


def _find_invariant(invariants: list[Invariant], *, name: str, invariants_path: Path) -> Invariant:
    for invariant in invariants:
        if invariant.name == name:
            return invariant
    raise LitmusUserError(f"Invariant '{name}' was not found in {invariants_path}.")


def _matches_review_filter(invariant: Invariant, *, filter_name: str) -> bool:
    if filter_name == "pending":
        return invariant.is_pending_suggestion()
    if filter_name == "dismissed":
        return invariant.is_dismissed_suggestion()
    if filter_name == "promoted":
        return invariant.review is not None and invariant.review.state is InvariantReviewState.PROMOTED
    if filter_name == "all":
        return invariant.is_pending_suggestion() or invariant.review is not None
    raise LitmusUserError("Unsupported review filter. Use one of: pending, dismissed, promoted, all.")


def _review_state_for_listing(invariant: Invariant) -> InvariantReviewState:
    if invariant.review is None:
        return InvariantReviewState.PENDING
    return invariant.review.state


def _review_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_can_confirm(target: Invariant) -> None:
    if target.source == "suggested:route_gap":
        raise LitmusUserError(
            "Route-gap warning invariants cannot be promoted to confirmed. "
            "Add or mine a real baseline instead."
        )


def _normalized_review_for_status(
    target: Invariant,
    *,
    status: InvariantStatus,
) -> InvariantReview | None:
    if status is InvariantStatus.SUGGESTED:
        return None
    if target.is_promoted_confirmation():
        return target.review
    return InvariantReview(
        state=InvariantReviewState.PROMOTED,
        reason=None if target.review is None else target.review.reason,
        reviewed_at=_review_timestamp(),
        review_source="cli",
    )
