from __future__ import annotations

import subprocess
from pathlib import Path


def test_litmus_help_shows_core_commands() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        ["litmus", "--help"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
    assert "init" in result.stdout
    assert "verify" in result.stdout
    assert "watch" in result.stdout
    assert "replay" in result.stdout
