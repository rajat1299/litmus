from __future__ import annotations

import ast
import importlib
from pathlib import Path

from litmus.config import load_repo_config
from litmus.discovery.project import iter_python_files, module_name_from_path

_SUPPORTED_APP_FACTORIES = {"FastAPI", "Starlette"}


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


def load_asgi_app(reference: str):
    module_name, attribute_name = reference.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
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
