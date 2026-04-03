from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from litmus.discovery.git_scope import list_changed_files_for_diff, list_staged_files
from litmus.discovery.routes import RouteDefinition
from litmus.discovery.tracing import map_changed_code_to_endpoints
from litmus.errors import VerificationScopeError
from litmus.invariants.models import Invariant
from litmus.invariants.store import default_invariants_path


VerifyScopeMode = Literal["full", "paths", "staged", "diff"]


@dataclass(slots=True)
class VerifyScope:
    mode: VerifyScopeMode
    changed_files: list[str]
    label: str


def default_verification_scope() -> VerifyScope:
    return VerifyScope(mode="full", changed_files=[], label="full repo")


def resolve_verification_scope(
    root: Path | str,
    *,
    explicit_paths: list[Path | str] | None = None,
    staged: bool = False,
    diff: str | None = None,
) -> VerifyScope:
    repo_root = Path(root)
    explicit_paths = explicit_paths or []

    selected_modes = sum([bool(explicit_paths), staged, diff is not None])
    if selected_modes > 1:
        raise VerificationScopeError("Choose exactly one verification scope mode")

    if explicit_paths:
        changed_files = _expand_explicit_paths(repo_root, explicit_paths)
        return VerifyScope(
            mode="paths",
            changed_files=changed_files,
            label=f"paths: {', '.join(changed_files)}",
        )

    if staged:
        try:
            changed_files = list_staged_files(repo_root)
        except LookupError as exc:
            raise VerificationScopeError(str(exc)) from exc
        return VerifyScope(mode="staged", changed_files=changed_files, label="staged diff")

    if diff is not None:
        try:
            changed_files = list_changed_files_for_diff(repo_root, diff)
        except LookupError as exc:
            raise VerificationScopeError(str(exc)) from exc
        return VerifyScope(mode="diff", changed_files=changed_files, label=f"diff {diff}")

    return default_verification_scope()


def apply_verification_scope(
    root: Path | str,
    routes: list[RouteDefinition],
    invariants: list[Invariant],
    scope: VerifyScope,
) -> tuple[list[RouteDefinition], list[Invariant]]:
    if scope.mode == "full":
        return routes, invariants

    if not scope.changed_files:
        return [], []

    selected_route_keys = {
        (route.method, route.path)
        for route in map_changed_code_to_endpoints(root, scope.changed_files)
    }
    scoped_invariants: list[Invariant] = []
    seen_ids: set[int] = set()

    for invariant in invariants:
        if not _is_selected_directly_by_changed_artifact(root, invariant, scope.changed_files):
            continue
        _append_unique_invariant(scoped_invariants, seen_ids, invariant)
        route_key = _route_key_for_invariant(invariant)
        if route_key is not None:
            selected_route_keys.add(route_key)

    for invariant in invariants:
        route_key = _route_key_for_invariant(invariant)
        if route_key is None or route_key not in selected_route_keys:
            continue
        _append_unique_invariant(scoped_invariants, seen_ids, invariant)

    scoped_routes = [
        route
        for route in routes
        if (route.method, route.path) in selected_route_keys
    ]
    return scoped_routes, scoped_invariants


def _expand_explicit_paths(root: Path, explicit_paths: list[Path | str]) -> list[str]:
    changed_files: list[str] = []

    for explicit_path in explicit_paths:
        candidate = Path(explicit_path)
        resolved = candidate if candidate.is_absolute() else root / candidate
        if not resolved.exists():
            raise VerificationScopeError(f"Path does not exist: {explicit_path}")

        if resolved.is_dir():
            nested_paths = sorted(path for path in resolved.rglob("*") if path.is_file())
            for path in nested_paths:
                _append_unique_path(changed_files, _normalize_relative_path(path, root))
            continue

        _append_unique_path(changed_files, _normalize_relative_path(resolved, root))

    return changed_files


def _normalize_relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise VerificationScopeError(f"Path is outside the repository: {path}") from exc


def _append_unique_path(changed_files: list[str], candidate: str) -> None:
    if candidate not in changed_files:
        changed_files.append(candidate)


def _is_mined_from_changed_test_file(
    root: Path | str,
    invariant: Invariant,
    changed_files: list[str],
) -> bool:
    if not invariant.source.startswith("mined:"):
        return False

    source_reference = invariant.source.removeprefix("mined:")
    source_file = source_reference.split("::", maxsplit=1)[0]
    normalized_source_file = _normalize_mined_source_path(Path(root), source_file)
    if normalized_source_file is None:
        return False
    return normalized_source_file in changed_files


def _is_selected_directly_by_changed_artifact(
    root: Path | str,
    invariant: Invariant,
    changed_files: list[str],
) -> bool:
    if _is_mined_from_changed_test_file(root, invariant, changed_files):
        return True

    if invariant.status.value != "suggested":
        return False

    curated_store_path = default_invariants_path(root)
    try:
        normalized_curated_path = curated_store_path.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return False
    return normalized_curated_path in changed_files


def _normalize_mined_source_path(root: Path, source_file: str) -> str | None:
    candidate = Path(source_file)
    if not candidate.is_absolute():
        return candidate.as_posix()

    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _route_key_for_invariant(invariant: Invariant) -> tuple[str, str] | None:
    request = invariant.request
    if request is None or request.method is None or request.path is None:
        return None
    return request.method.upper(), request.path


def _append_unique_invariant(
    scoped_invariants: list[Invariant],
    seen_ids: set[int],
    invariant: Invariant,
) -> None:
    identifier = id(invariant)
    if identifier in seen_ids:
        return
    seen_ids.add(identifier)
    scoped_invariants.append(invariant)
