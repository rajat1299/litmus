from __future__ import annotations

from pathlib import Path


def test_action_yaml_exposes_outputs_and_runs_report_module() -> None:
    action_yml = Path("action.yml").read_text(encoding="utf-8")

    assert "using: composite" in action_yml
    assert "min-score" in action_yml
    assert "comment-path" in action_yml
    assert "python -m litmus.github_action.report" in action_yml
    assert "LITMUS_WORKSPACE" in action_yml


def test_repo_workflow_runs_on_pull_requests_using_local_action() -> None:
    workflow = Path(".github/workflows/litmus.yml").read_text(encoding="utf-8")

    assert "name: Litmus Verification" in workflow
    assert "pull_request:" in workflow
    assert "uses: ./" in workflow
    assert "min-score: '80'" in workflow
    assert "comment: 'true'" in workflow
