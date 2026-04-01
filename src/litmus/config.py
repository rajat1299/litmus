from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

import yaml


@dataclass(slots=True)
class RepoConfig:
    app: str | None = None


def load_repo_config(root: Path | str) -> RepoConfig:
    repo_root = Path(root)

    litmus_yaml = repo_root / "litmus.yaml"
    if litmus_yaml.exists():
        data = yaml.safe_load(litmus_yaml.read_text(encoding="utf-8")) or {}
        return RepoConfig(app=data.get("app"))

    pyproject_file = repo_root / "pyproject.toml"
    if pyproject_file.exists():
        data = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
        tool_config = data.get("tool", {}).get("litmus", {})
        return RepoConfig(app=tool_config.get("app"))

    return RepoConfig()


def write_repo_config(path: Path | str, config: RepoConfig) -> None:
    output_path = Path(path)
    output_path.write_text(
        yaml.safe_dump({"app": config.app}, sort_keys=False),
        encoding="utf-8",
    )
