from __future__ import annotations

import ast
from contextlib import contextmanager
import importlib
from pathlib import Path
import sys
from types import ModuleType

from litmus.config import load_repo_config
from litmus.discovery.project import iter_python_files, module_name_from_path

_SUPPORTED_APP_FACTORIES = {"FastAPI", "Starlette"}
_INTERNAL_MODULE_ROOT = Path(__file__).resolve().parents[2]
_LOADED_APP_ROOTS: set[Path] = set()


def discover_app_reference(root: Path | str) -> str:
    repo_root = Path(root)
    config = load_repo_config(repo_root)
    if config.app:
        return config.app

    for python_file in iter_python_files(repo_root):
        reference = _discover_reference_in_file(python_file, repo_root)
        if reference is not None:
            return reference

    raise LookupError(f"Could not discover an ASGI app in {repo_root}")


def load_asgi_app(reference: str, root: Path | str | None = None):
    module_name, attribute_name = reference.split(":", maxsplit=1)
    root_path = None if root is None else Path(root).resolve()
    with _temporary_import_root(root):
        _evict_repo_owned_modules(root_path, module_name)
        module = importlib.import_module(module_name)
    if root_path is not None:
        _LOADED_APP_ROOTS.add(root_path)
    return getattr(module, attribute_name)


def _discover_reference_in_file(path: Path, root: Path) -> str | None:
    tree = ast.parse(path.read_text(encoding="utf-8"))

    for node in tree.body:
        if isinstance(node, ast.Assign) and _is_supported_app_call(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    return f"{module_name_from_path(path, root)}:{target.id}"

        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if _is_supported_app_call(node.value):
                return f"{module_name_from_path(path, root)}:{node.target.id}"

    return None


def _is_supported_app_call(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Call):
        return False

    factory_name = None
    if isinstance(node.func, ast.Name):
        factory_name = node.func.id
    elif isinstance(node.func, ast.Attribute):
        factory_name = node.func.attr

    return factory_name in _SUPPORTED_APP_FACTORIES


@contextmanager
def _temporary_import_root(root: Path | str | None):
    if root is None:
        importlib.invalidate_caches()
        yield
        return

    root_path = str(Path(root).resolve())
    already_present = root_path in sys.path

    if not already_present:
        sys.path.insert(0, root_path)
    importlib.invalidate_caches()

    try:
        yield
    finally:
        if not already_present:
            sys.path.remove(root_path)
        importlib.invalidate_caches()


def _evict_repo_owned_modules(root: Path | None, module_name: str) -> None:
    top_level_module = module_name.split(".", maxsplit=1)[0]
    for name, module in list(sys.modules.items()):
        if _module_is_internal_to_litmus(module):
            continue
        if _module_name_conflicts(name, top_level_module):
            sys.modules.pop(name, None)
            continue
        if not _module_is_owned_by_loaded_app_root(module, root):
            continue
        sys.modules.pop(name, None)


def _module_is_owned_by_loaded_app_root(module: ModuleType | None, current_root: Path | None) -> bool:
    if module is None:
        return False

    candidate_roots = set(_LOADED_APP_ROOTS)
    if current_root is not None:
        candidate_roots.add(current_root)

    for path in _module_paths(module):
        if _path_is_within(path, _INTERNAL_MODULE_ROOT):
            return False
        for repo_root in candidate_roots:
            if _path_is_within(path, repo_root):
                return True
    return False


def _module_is_internal_to_litmus(module: ModuleType | None) -> bool:
    if module is None:
        return False

    for path in _module_paths(module):
        if _path_is_within(path, _INTERNAL_MODULE_ROOT):
            return True
    return False


def _module_name_conflicts(name: str, top_level_module: str) -> bool:
    return name == top_level_module or name.startswith(f"{top_level_module}.")


def _module_paths(module: ModuleType) -> list[Path]:
    paths: list[Path] = []

    file_path = getattr(module, "__file__", None)
    if file_path:
        paths.append(Path(file_path).resolve())

    spec = getattr(module, "__spec__", None)
    if spec is None:
        return paths

    origin = getattr(spec, "origin", None)
    if origin and origin not in {"built-in", "frozen"}:
        origin_path = Path(origin).resolve()
        if origin_path not in paths:
            paths.append(origin_path)

    search_locations = getattr(spec, "submodule_search_locations", None)
    if search_locations is not None:
        for location in search_locations:
            location_path = Path(location).resolve()
            if location_path not in paths:
                paths.append(location_path)

    return paths


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
