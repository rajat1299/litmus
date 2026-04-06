from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import litmus
from typer.main import get_command

from litmus.cli import app, init, mcp, replay, verify, watch
from litmus.surface import (
    INIT_OPERATION,
    MCP_OPERATION,
    REPLAY_OPERATION,
    VERIFY_OPERATION,
    WATCH_OPERATION,
)


def test_litmus_replay_no_longer_exports_run_store_lookup() -> None:
    import litmus.replay as replay

    assert not hasattr(replay, "replay_record_for_seed")


def test_importing_litmus_cli_does_not_eagerly_import_mcp_tools() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import litmus.cli, sys; "
                "print('litmus.mcp.tools' in sys.modules)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_importing_litmus_mcp_tools_in_isolation_does_not_hit_package_cycles() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import litmus.mcp.tools",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 0, result.stderr


def test_pyproject_declares_anyio_as_runtime_dependency() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.startswith("anyio>=") for dependency in dependencies)


def test_pyproject_uses_dynamic_version_from_package_module() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert "version" not in project
    assert "dynamic" in project
    assert "version" in project["dynamic"]
    assert pyproject["tool"]["hatch"]["version"]["path"] == "src/litmus/__init__.py"
    assert litmus.__version__ == "0.1.0"


def test_pyproject_uses_grounded_package_readme() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    readme_path = Path(pyproject["project"]["readme"])

    assert readme_path == Path("docs/package-readme.md")
    assert readme_path.exists()

    package_readme = readme_path.read_text(encoding="utf-8")
    assert "The top-level `README.md` remains aspirational." in package_readme
    assert "Homebrew remains deferred." in package_readme


def test_cli_command_help_comes_from_surface_contract_without_duplicate_docstrings() -> None:
    command_group = get_command(app)
    assert command_group.commands["init"].help == INIT_OPERATION.cli_help
    assert command_group.commands["verify"].help == VERIFY_OPERATION.cli_help
    assert command_group.commands["watch"].help == WATCH_OPERATION.cli_help
    assert command_group.commands["mcp"].help == MCP_OPERATION.cli_help
    assert command_group.commands["replay"].help == REPLAY_OPERATION.cli_help

    assert init.__doc__ is None
    assert verify.__doc__ is None
    assert watch.__doc__ is None
    assert mcp.__doc__ is None
    assert replay.__doc__ is None
