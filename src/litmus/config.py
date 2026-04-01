from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

import yaml


@dataclass(slots=True)
class RepoConfig:
    app: str | None = None
    suggested_invariants: bool = False


def load_repo_config(root: Path | str) -> RepoConfig:
    repo_root = Path(root)

    litmus_yaml = repo_root / "litmus.yaml"
    if litmus_yaml.exists():
        data = yaml.safe_load(litmus_yaml.read_text(encoding="utf-8")) or {}
        return RepoConfig(
            app=data.get("app"),
            suggested_invariants=bool(data.get("suggested_invariants", False)),
        )

    pyproject_file = repo_root / "pyproject.toml"
    if pyproject_file.exists():
        data = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
        tool_config = data.get("tool", {}).get("litmus", {})
        return RepoConfig(
            app=tool_config.get("app"),
            suggested_invariants=bool(tool_config.get("suggested_invariants", False)),
        )

    return RepoConfig()


def write_repo_config(path: Path | str, config: RepoConfig) -> None:
    output_path = Path(path)
    payload: dict[str, object] = {}
    if config.app is not None:
        payload["app"] = config.app
    if config.suggested_invariants:
        payload["suggested_invariants"] = True
    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
