from __future__ import annotations

from pathlib import Path

import pytest

from litmus.config import DecisionPolicy, FaultProfile, RepoConfig, load_repo_config, write_repo_config
from litmus.errors import ConfigParseError


def test_load_repo_config_reads_litmus_yaml(tmp_path: Path) -> None:
    (tmp_path / "litmus.yaml").write_text('app: "service.main:app"\n', encoding="utf-8")

    config = load_repo_config(tmp_path)

    assert config.app == "service.main:app"
    assert config.suggested_invariants is False


def test_load_repo_config_falls_back_to_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "sample"
version = "0.1.0"

[tool.litmus]
app = "package.entry:app"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_repo_config(tmp_path)

    assert config.app == "package.entry:app"
    assert config.suggested_invariants is False


def test_load_repo_config_reads_suggested_invariants_flag(tmp_path: Path) -> None:
    (tmp_path / "litmus.yaml").write_text(
        'app: "service.main:app"\nsuggested_invariants: true\n',
        encoding="utf-8",
    )

    config = load_repo_config(tmp_path)

    assert config.app == "service.main:app"
    assert config.suggested_invariants is True


def test_load_repo_config_parses_string_false_as_false(tmp_path: Path) -> None:
    (tmp_path / "litmus.yaml").write_text(
        'app: "service.main:app"\nsuggested_invariants: "false"\n',
        encoding="utf-8",
    )

    config = load_repo_config(tmp_path)

    assert config.suggested_invariants is False


def test_load_repo_config_parses_string_false_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "sample"
version = "0.1.0"

[tool.litmus]
app = "package.entry:app"
suggested_invariants = "false"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_repo_config(tmp_path)

    assert config.app == "package.entry:app"
    assert config.suggested_invariants is False


def test_load_repo_config_reads_fault_profile_from_litmus_yaml(tmp_path: Path) -> None:
    (tmp_path / "litmus.yaml").write_text(
        'app: "service.main:app"\nfault_profile: hostile\n',
        encoding="utf-8",
    )

    config = load_repo_config(tmp_path)

    assert config.app == "service.main:app"
    assert config.fault_profile is FaultProfile.HOSTILE


def test_load_repo_config_reads_decision_policy_from_litmus_yaml(tmp_path: Path) -> None:
    (tmp_path / "litmus.yaml").write_text(
        'app: "service.main:app"\ndecision_policy: strict_local_v1\n',
        encoding="utf-8",
    )

    config = load_repo_config(tmp_path)

    assert config.app == "service.main:app"
    assert config.decision_policy is DecisionPolicy.STRICT_LOCAL_V1


def test_load_repo_config_raises_config_parse_error_for_invalid_fault_profile(tmp_path: Path) -> None:
    (tmp_path / "litmus.yaml").write_text(
        'app: "service.main:app"\nfault_profile: chaos\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigParseError, match="fault_profile"):
        load_repo_config(tmp_path)


def test_load_repo_config_raises_config_parse_error_for_invalid_decision_policy(tmp_path: Path) -> None:
    (tmp_path / "litmus.yaml").write_text(
        'app: "service.main:app"\ndecision_policy: aggressive\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigParseError, match="decision_policy"):
        load_repo_config(tmp_path)


def test_write_repo_config_can_materialize_explicit_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "litmus.yaml"

    write_repo_config(
        config_path,
        RepoConfig(
            app="service.main:app",
            suggested_invariants=False,
            fault_profile=FaultProfile.DEFAULT,
            decision_policy=DecisionPolicy.ALPHA_LOCAL_V1,
        ),
        include_defaults=True,
    )

    assert config_path.read_text(encoding="utf-8") == (
        "app: service.main:app\n"
        "suggested_invariants: false\n"
        "fault_profile: default\n"
        "decision_policy: alpha_local_v1\n"
    )
