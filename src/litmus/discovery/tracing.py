from __future__ import annotations

from collections.abc import Mapping, Set
from pathlib import Path

from litmus.discovery.project import iter_python_files
from litmus.discovery.routes import RouteDefinition, extract_routes


def map_changed_code_to_endpoints(
    root: Path | str,
    changed_files: list[str],
    changed_symbols: Mapping[str, Set[str]] | None = None,
) -> list[RouteDefinition]:
    repo_root = Path(root)
    normalized_changed_files = {Path(path).as_posix() for path in changed_files}
    route_matches: list[RouteDefinition] = []

    for python_file in iter_python_files(repo_root):
        for route in extract_routes(python_file, repo_root):
            if _route_matches_change(route, normalized_changed_files, changed_symbols):
                route_matches.append(route)

    return route_matches


def _route_matches_change(
    route: RouteDefinition,
    changed_files: set[str],
    changed_symbols: Mapping[str, Set[str]] | None,
) -> bool:
    if route.file_path in changed_files:
        return True

    for changed_file in changed_files:
        if _matches_imported_symbol(route, changed_file, changed_symbols):
            return True

    return False


def _matches_imported_symbol(
    route: RouteDefinition,
    changed_file: str,
    changed_symbols: Mapping[str, Set[str]] | None,
) -> bool:
    if changed_symbols is None:
        return False

    symbols = changed_symbols.get(changed_file)
    if not symbols:
        return False

    for symbol in symbols:
        if route.imported_symbols.get(symbol) == changed_file and symbol in route.called_targets:
            return True

        for alias, module_path in route.imported_module_aliases.items():
            if module_path == changed_file and f"{alias}.{symbol}" in route.called_targets:
                return True

    return False
