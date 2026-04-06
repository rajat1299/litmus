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
    assert "Grounded alpha verification for Python async ASGI services." in result.stdout
    assert "init" in result.stdout
    assert "verify" in result.stdout
    assert "watch" in result.stdout
    assert "mcp" in result.stdout
    assert "replay" in result.stdout
    assert "invariants" in result.stdout
    assert "config" in result.stdout
    assert "Run the local Litmus MCP server over stdio." in result.stdout
    assert "Replay a recorded seed from the latest replayable Litmus run." in result.stdout
