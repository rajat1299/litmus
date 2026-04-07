from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from litmus.config import FaultProfile, RepoConfig, load_repo_config, write_repo_config
from litmus.errors import LitmusUserError
from litmus.invariants.models import Invariant, InvariantStatus
from litmus.invariants.store import default_invariants_path, load_invariants, save_invariants


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
class ConfigSetResult:
    config_path: Path
    key: str
    value: str


def list_invariants(root: Path | str) -> InvariantListResult:
    invariants_path = default_invariants_path(root)
    invariants = _load_curated_invariants(invariants_path)
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


def set_invariant_status(
    root: Path | str,
    *,
    name: str,
    status: InvariantStatus,
) -> InvariantStatusUpdateResult:
    invariants_path = default_invariants_path(root)
    invariants = _load_curated_invariants(invariants_path)
    target = _find_invariant(invariants, name=name, invariants_path=invariants_path)
    updated = target.model_copy(update={"status": status})
    updated_invariants = [updated if invariant.name == name else invariant for invariant in invariants]
    save_invariants(invariants_path, updated_invariants)
    return InvariantStatusUpdateResult(invariants_path=invariants_path, invariant=updated)


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
