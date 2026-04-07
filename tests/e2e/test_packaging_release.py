from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _assert_local_launch_budget(summary: dict[str, object]) -> None:
    performance = summary["performance"]
    assert performance == {
        "mode": "local",
        "fault_profile": "default",
        "measured": True,
        "elapsed_ms": performance["elapsed_ms"],
        "budget_ms": 10_000,
        "within_budget": True,
        "replay_seeds_per_scenario": 3,
        "property_max_examples": 100,
    }
    assert isinstance(performance["elapsed_ms"], int)
    assert 0 <= performance["elapsed_ms"] <= performance["budget_ms"]


def test_alpha_docs_and_built_wheel_support_the_demo_flow(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    quickstart_path = repo_root / "docs" / "alpha-quickstart.md"
    package_readme_path = repo_root / "docs" / "package-readme.md"
    release_notes_path = repo_root / "docs" / "releases" / "2026-03-31-alpha.md"
    contributing_path = repo_root / "CONTRIBUTING.md"

    assert quickstart_path.exists()
    assert package_readme_path.exists()
    assert release_notes_path.exists()
    assert contributing_path.exists()

    quickstart = quickstart_path.read_text(encoding="utf-8")
    package_readme = package_readme_path.read_text(encoding="utf-8")
    release_notes = release_notes_path.read_text(encoding="utf-8")
    contributing = contributing_path.read_text(encoding="utf-8")

    assert "uv build" in quickstart
    assert "pip install litmus-cli" in package_readme
    assert "The top-level `README.md` remains aspirational." in package_readme
    assert "Homebrew remains deferred." in package_readme
    assert "examples/payment_service" in quickstart
    assert "litmus verify" in quickstart
    assert "local `litmus verify` runs are budgeted to stay within 10 seconds" in quickstart
    assert "CI verification runs are budgeted within 60 seconds" in quickstart
    assert "Performance: elapsed=" in quickstart
    assert "Launch budgets: replay_seeds/scenario=3 property_examples=100" in quickstart
    assert "Homebrew" in quickstart
    assert "deferred" in quickstart
    assert "manual dispatch can rerun the workflow as a build-only preflight" in quickstart
    assert "Known limitations" in release_notes
    assert "Local `litmus verify` is budgeted for 10 seconds" in release_notes
    assert "CI verification is budgeted for 60 seconds" in release_notes
    assert "3 replay seeds per scenario and 100 property examples in local mode" in release_notes
    assert "500 replay seeds per scenario and 500 property examples in CI mode" in release_notes
    assert "Homebrew" in release_notes
    assert "deferred" in release_notes
    assert "manual dispatch can run as a preflight build" in release_notes
    assert "examples/payment_service" in release_notes
    assert "examples/payment_service" in contributing
    assert "uv run litmus verify" not in contributing
    assert "Local verify is budgeted for 10 seconds" in package_readme
    assert "CI verification is budgeted for 60 seconds" in package_readme
    assert "3 replay seeds per scenario and 100 property examples in local mode" in package_readme
    assert "500 replay seeds per scenario and 500 property examples in CI mode" in package_readme

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
    assert "Performance:" in verify_result.stdout
    assert "budget<=10.00s mode=local profile=default within_budget=yes" in verify_result.stdout
    assert "Launch budgets: replay_seeds/scenario=3 property_examples=100" in verify_result.stdout
    latest_run_id = json.loads((demo_repo / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((demo_repo / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))
    summary = run_payload["activities"][0]["summary"]
    assert summary["replay"] == {
        "unchanged": 1,
        "breaking_change": 1,
        "benign_change": 0,
        "improvement": 0,
    }
    _assert_local_launch_budget(summary)

    replay_result = subprocess.run(
        [str(litmus_bin), "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=demo_repo,
        check=False,
    )
    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: breaking_change" in replay_result.stdout
