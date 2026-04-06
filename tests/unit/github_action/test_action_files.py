from __future__ import annotations

from pathlib import Path


def test_action_yaml_exposes_outputs_and_runs_report_module() -> None:
    action_yml = Path("action.yml").read_text(encoding="utf-8")

    assert "using: composite" in action_yml
    assert "token:" in action_yml
    assert "min-score" in action_yml
    assert "comment-path" in action_yml
    assert "python -m litmus.github_action.report" in action_yml
    assert "LITMUS_WORKSPACE" in action_yml
    assert "LITMUS_GITHUB_TOKEN" in action_yml


def test_repo_workflow_runs_on_pull_requests_using_local_action() -> None:
    workflow = Path(".github/workflows/litmus.yml").read_text(encoding="utf-8")

    assert "name: Litmus Verification" in workflow
    assert "pull_request:" in workflow
    assert "uses: ./" in workflow
    assert "token: ${{ github.token }}" in workflow
    assert "min-score: '80'" in workflow
    assert "comment: 'true'" in workflow


def test_release_workflow_builds_and_publishes_python_package() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "name: Litmus Release" in workflow
    assert "workflow_dispatch:" in workflow
    assert "publish:" in workflow
    assert "Manual preflight stays build-only unless publish is explicitly enabled" in workflow
    assert "default: false" in workflow
    assert "push:" in workflow
    assert "tags:" in workflow
    assert "v*" in workflow
    assert "uv build --out-dir dist" in workflow
    assert "pypa/gh-action-pypi-publish" in workflow
    assert "inputs.publish == true" in workflow
    assert "startsWith(github.ref, 'refs/tags/v')" in workflow
    assert "permissions:" in workflow
    assert "id-token: write" in workflow
