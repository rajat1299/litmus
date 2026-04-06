from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tomllib

import yaml


class FaultProfile(str, Enum):
    DEFAULT = "default"
    GENTLE = "gentle"
    HOSTILE = "hostile"


@dataclass(slots=True)
class RepoConfig:
    app: str | None = None
    suggested_invariants: bool = False
    fault_profile: FaultProfile = FaultProfile.DEFAULT


def load_repo_config(root: Path | str) -> RepoConfig:
    repo_root = Path(root)

    litmus_yaml = repo_root / "litmus.yaml"
    if litmus_yaml.exists():
        data = yaml.safe_load(litmus_yaml.read_text(encoding="utf-8")) or {}
        return RepoConfig(
            app=data.get("app"),
            suggested_invariants=bool(data.get("suggested_invariants", False)),
            fault_profile=_coerce_fault_profile(data.get("fault_profile")),
        )

    pyproject_file = repo_root / "pyproject.toml"
    if pyproject_file.exists():
        data = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
        tool_config = data.get("tool", {}).get("litmus", {})
        return RepoConfig(
            app=tool_config.get("app"),
            suggested_invariants=bool(tool_config.get("suggested_invariants", False)),
            fault_profile=_coerce_fault_profile(tool_config.get("fault_profile")),
        )

    return RepoConfig()


def write_repo_config(path: Path | str, config: RepoConfig, *, include_defaults: bool = False) -> None:
    output_path = Path(path)
    payload: dict[str, object] = {}
    if config.app is not None:
        payload["app"] = config.app
    if include_defaults or config.suggested_invariants:
        payload["suggested_invariants"] = config.suggested_invariants
    if include_defaults or config.fault_profile is not FaultProfile.DEFAULT:
        payload["fault_profile"] = config.fault_profile.value
    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _coerce_fault_profile(value: object) -> FaultProfile:
    if value in (None, ""):
        return FaultProfile.DEFAULT
    return FaultProfile(str(value).strip().lower())
