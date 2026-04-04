from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


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
