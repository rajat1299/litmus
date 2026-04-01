from __future__ import annotations

from pathlib import Path

from litmus.config import load_repo_config


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
