from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tomllib

import yaml

from litmus.errors import ConfigParseError


class FaultProfile(str, Enum):
    DEFAULT = "default"
    GENTLE = "gentle"
    HOSTILE = "hostile"


class DecisionPolicy(str, Enum):
    ALPHA_LOCAL_V1 = "alpha_local_v1"
    STRICT_LOCAL_V1 = "strict_local_v1"


@dataclass(slots=True)
class RepoConfig:
    app: str | None = None
    suggested_invariants: bool = False
    fault_profile: FaultProfile = FaultProfile.DEFAULT
    decision_policy: DecisionPolicy = DecisionPolicy.ALPHA_LOCAL_V1


def load_repo_config(root: Path | str, *, overrides: dict[str, object] | None = None) -> RepoConfig:
    data = _read_repo_config_payload(root)
    if overrides:
        data = {**data, **overrides}

    return RepoConfig(
        app=_coerce_app_reference(data.get("app")),
        suggested_invariants=_coerce_bool(data.get("suggested_invariants", False), field_name="suggested_invariants"),
        fault_profile=_coerce_fault_profile(data.get("fault_profile")),
        decision_policy=_coerce_decision_policy(data.get("decision_policy")),
    )


def write_repo_config(path: Path | str, config: RepoConfig, *, include_defaults: bool = False) -> None:
    output_path = Path(path)
    payload: dict[str, object] = {}
    if config.app is not None:
        payload["app"] = config.app
    if include_defaults or config.suggested_invariants:
        payload["suggested_invariants"] = config.suggested_invariants
    if include_defaults or config.fault_profile is not FaultProfile.DEFAULT:
        payload["fault_profile"] = config.fault_profile.value
    if include_defaults or config.decision_policy is not DecisionPolicy.ALPHA_LOCAL_V1:
        payload["decision_policy"] = config.decision_policy.value
    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _read_repo_config_payload(root: Path | str) -> dict[str, object]:
    repo_root = Path(root)

    litmus_yaml = repo_root / "litmus.yaml"
    if litmus_yaml.exists():
        data = yaml.safe_load(litmus_yaml.read_text(encoding="utf-8")) or {}
        return _expect_mapping(data, source=litmus_yaml)

    pyproject_file = repo_root / "pyproject.toml"
    if pyproject_file.exists():
        data = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
        tool_config = data.get("tool", {}).get("litmus", {})
        return _expect_mapping(tool_config, source=pyproject_file, section="tool.litmus")

    return {}


def _expect_mapping(
    value: object,
    *,
    source: Path,
    section: str | None = None,
) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    location = section if section is not None else source.name
    raise ConfigParseError(f"Invalid Litmus config in {location}: expected a key-value mapping.")


def _coerce_app_reference(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ConfigParseError("Invalid Litmus config field 'app': expected a string app reference.")


def _coerce_bool(value: object, *, field_name: str) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ConfigParseError(
        f"Invalid Litmus config field '{field_name}': expected one of true, false, 1, 0, yes, no, on, off."
    )


def _coerce_fault_profile(value: object) -> FaultProfile:
    if value is None:
        return FaultProfile.DEFAULT
    if isinstance(value, FaultProfile):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        try:
            return FaultProfile(normalized)
        except ValueError as exc:
            valid_profiles = ", ".join(profile.value for profile in FaultProfile)
            raise ConfigParseError(
                f"Invalid Litmus config field 'fault_profile': expected one of {valid_profiles}."
            ) from exc
    raise ConfigParseError("Invalid Litmus config field 'fault_profile': expected a string value.")


def coerce_decision_policy(value: DecisionPolicy | str) -> DecisionPolicy:
    if isinstance(value, DecisionPolicy):
        return value
    return _coerce_decision_policy(value)


def _coerce_decision_policy(value: object) -> DecisionPolicy:
    if value is None:
        return DecisionPolicy.ALPHA_LOCAL_V1
    if isinstance(value, DecisionPolicy):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        try:
            return DecisionPolicy(normalized)
        except ValueError as exc:
            valid_policies = ", ".join(policy.value for policy in DecisionPolicy)
            raise ConfigParseError(
                f"Invalid Litmus config field 'decision_policy': expected one of {valid_policies}."
            ) from exc
    raise ConfigParseError("Invalid Litmus config field 'decision_policy': expected a string value.")
