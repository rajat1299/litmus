from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_alpha_docs_and_built_wheel_support_the_demo_flow(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    quickstart_path = repo_root / "docs" / "alpha-quickstart.md"
    release_notes_path = repo_root / "docs" / "releases" / "2026-03-31-alpha.md"
    contributing_path = repo_root / "CONTRIBUTING.md"

    assert quickstart_path.exists()
    assert release_notes_path.exists()
    assert contributing_path.exists()

    quickstart = quickstart_path.read_text(encoding="utf-8")
    release_notes = release_notes_path.read_text(encoding="utf-8")
    contributing = contributing_path.read_text(encoding="utf-8")

    assert "uv build" in quickstart
    assert "examples/payment_service" in quickstart
    assert "litmus verify" in quickstart
    assert "Homebrew" in quickstart
    assert "deferred" in quickstart
    assert "Known limitations" in release_notes
    assert "Homebrew" in release_notes
    assert "deferred" in release_notes
    assert "examples/payment_service" in release_notes
    assert "examples/payment_service" in contributing
    assert "uv run litmus verify" not in contributing

    dist_dir = tmp_path / "dist"
    build_result = subprocess.run(
        ["uv", "build", "--out-dir", str(dist_dir)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert build_result.returncode == 0, build_result.stderr

    wheel_path = next(dist_dir.glob("*.whl"))
    assert any(dist_dir.glob("*.tar.gz"))

    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    scripts_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    venv_python = scripts_dir / ("python.exe" if os.name == "nt" else "python")
    litmus_bin = scripts_dir / ("litmus.exe" if os.name == "nt" else "litmus")

    install_result = subprocess.run(
        ["uv", "pip", "install", "--python", str(venv_python), str(wheel_path)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert install_result.returncode == 0, install_result.stderr

    help_result = subprocess.run(
        [str(litmus_bin), "--help"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert help_result.returncode == 0, help_result.stderr
    assert "Grounded alpha verification for Python async ASGI services." in help_result.stdout

    demo_repo = tmp_path / "payment_service"
    shutil.copytree(
        repo_root / "examples" / "payment_service",
        demo_repo,
        ignore=shutil.ignore_patterns(".litmus", "__pycache__", "*.pyc"),
    )

    verify_result = subprocess.run(
        [str(litmus_bin), "verify"],
        capture_output=True,
        text=True,
        cwd=demo_repo,
        check=False,
    )
    assert verify_result.returncode == 1, verify_result.stdout
    assert "Litmus verify" in verify_result.stdout
    latest_run_id = json.loads((demo_repo / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((demo_repo / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))
    assert run_payload["activities"][0]["summary"]["replay"] == {
        "unchanged": 1,
        "breaking_change": 1,
        "benign_change": 0,
        "improvement": 0,
    }

    replay_result = subprocess.run(
        [str(litmus_bin), "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=demo_repo,
        check=False,
    )
    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: breaking_change" in replay_result.stdout
