from __future__ import annotations

from pathlib import Path


def iter_python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def module_name_from_path(path: Path, root: Path) -> str:
    relative_path = path.relative_to(root)
    parts = list(relative_path.parts)

    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = path.stem

    return ".".join(parts)
