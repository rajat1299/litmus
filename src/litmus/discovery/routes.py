from __future__ import annotations

import ast
from dataclasses import dataclass, field
import importlib.util
from pathlib import Path

from litmus.discovery.project import module_name_from_path


_HTTP_METHOD_NAMES = {"get", "post", "put", "patch", "delete", "options", "head"}


@dataclass(slots=True)
class ImportedSymbol:
    module_path: str
    original_name: str


@dataclass(slots=True)
class RouteDefinition:
    method: str
    path: str
    handler_name: str
    file_path: str
    imported_symbols: dict[str, ImportedSymbol] = field(default_factory=dict)
    imported_module_aliases: dict[str, str] = field(default_factory=dict)
    called_targets: set[str] = field(default_factory=set)


def extract_routes(path: Path | str, root: Path | str) -> list[RouteDefinition]:
    file_path = Path(path)
    repo_root = Path(root)
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    relative_path = file_path.relative_to(repo_root).as_posix()
    module_name = module_name_from_path(file_path, repo_root)

    imported_symbols: dict[str, ImportedSymbol] = {}
    imported_module_aliases: dict[str, str] = {}

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module_path = _resolve_import_from_path(node, module_name, repo_root)
            if module_path is None:
                continue
            for alias in node.names:
                imported_symbols[alias.asname or alias.name] = ImportedSymbol(
                    module_path=module_path,
                    original_name=alias.name,
                )

        if isinstance(node, ast.Import):
            for alias in node.names:
                module_path = _resolve_module_path(alias.name, repo_root)
                if module_path is None:
                    continue
                imported_module_aliases[alias.asname or alias.name] = module_path

    routes: list[RouteDefinition] = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            route_signatures = _extract_route_signatures(decorator)
            if not route_signatures:
                continue

            called_targets = _collect_called_targets(node)
            for method, route_path in route_signatures:
                routes.append(
                    RouteDefinition(
                        method=method,
                        path=route_path,
                        handler_name=node.name,
                        file_path=relative_path,
                        imported_symbols=dict(imported_symbols),
                        imported_module_aliases=dict(imported_module_aliases),
                        called_targets=set(called_targets),
                    )
                )

    return routes


def _extract_route_signatures(decorator: ast.AST) -> list[tuple[str, str]]:
    if not isinstance(decorator, ast.Call):
        return []

    route_path = _literal_string(decorator.args[0]) if decorator.args else None
    if route_path is None:
        return []

    if isinstance(decorator.func, ast.Attribute):
        decorator_name = decorator.func.attr.lower()
        if decorator_name in _HTTP_METHOD_NAMES:
            return [(decorator_name.upper(), route_path)]
        if decorator_name == "route":
            methods = _extract_route_methods(decorator)
            if methods:
                return [(method, route_path) for method in methods]

    return []


def _extract_route_methods(decorator: ast.Call) -> list[str]:
    for keyword in decorator.keywords:
        if keyword.arg != "methods" or not isinstance(keyword.value, (ast.List, ast.Tuple)):
            continue
        methods = [value.value.upper() for value in keyword.value.elts if isinstance(value, ast.Constant) and isinstance(value.value, str)]
        if methods:
            return methods
    return []


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_called_targets(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    targets: set[str] = set()

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            targets.add(child.func.id)
        elif isinstance(child.func, ast.Attribute) and isinstance(child.func.value, ast.Name):
            targets.add(f"{child.func.value.id}.{child.func.attr}")

    return targets


def _resolve_module_path(module_name: str, root: Path) -> str | None:
    module_file = root.joinpath(*module_name.split(".")).with_suffix(".py")
    if module_file.exists():
        return module_file.relative_to(root).as_posix()

    package_init = root.joinpath(*module_name.split("."), "__init__.py")
    if package_init.exists():
        return package_init.relative_to(root).as_posix()

    return None


def _resolve_import_from_path(node: ast.ImportFrom, current_module_name: str, root: Path) -> str | None:
    module_reference = node.module or ""

    if node.level:
        if current_module_name.endswith(".__init__"):
            package_name = current_module_name.removesuffix(".__init__")
        else:
            package_name = current_module_name.rsplit(".", maxsplit=1)[0] if "." in current_module_name else ""

        relative_name = "." * node.level + module_reference
        try:
            resolved_name = importlib.util.resolve_name(relative_name, package_name)
        except ImportError:
            return None
        return _resolve_module_path(resolved_name, root)

    if not module_reference:
        return None

    return _resolve_module_path(module_reference, root)
