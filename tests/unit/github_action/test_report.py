from __future__ import annotations

from pathlib import Path

from litmus.dst.engine import VerificationResult
from litmus.invariants.models import RequestExample, ResponseExample
from litmus.replay.differential import DifferentialReplayResult, ReplayClassification
from litmus.replay.trace import ReplayTraceRecord
from litmus.github_action.report import (
    build_action_report,
    parse_min_score,
    run_github_action,
    write_action_report,
)
from litmus.scenarios.builder import Scenario


def test_build_action_report_writes_outputs_for_failing_verification(tmp_path) -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=500, json={"status": "broken"}),
                classification=ReplayClassification.BREAKING_CHANGE,
                diff={
                    "status_code": (200, 500),
                    "body": ({"status": "charged"}, {"status": "broken"}),
                },
            )
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:7",
                seed_value=7,
                app_reference="service.app:app",
                method="POST",
                path="/payments/charge",
                request_payload={"amount": 100},
                baseline_status_code=200,
                baseline_body={"status": "charged"},
                trace=[],
            )
        ],
        property_results=[],
    )

    report = build_action_report(result, min_score=parse_min_score("80"), include_comment=True)
    output_path = tmp_path / "github-output.txt"
    summary_path = tmp_path / "step-summary.md"
    comment_path = tmp_path / "litmus-pr-comment.md"

    write_action_report(
        report,
        output_path=output_path,
        summary_path=summary_path,
        comment_path=comment_path,
    )

    assert report.verdict == "fail"
    assert report.should_fail is True
    assert report.confidence == 0.0
    assert "## Litmus Verification" in report.comment
    assert "Litmus verify" in report.summary
    assert f"comment-path={comment_path}" in output_path.read_text(encoding="utf-8")
    assert "confidence=0.00" in output_path.read_text(encoding="utf-8")
    assert "verdict=fail" in output_path.read_text(encoding="utf-8")
    assert "## Litmus Verification" in comment_path.read_text(encoding="utf-8")
    assert "### Affected Endpoints" in summary_path.read_text(encoding="utf-8")


def test_parse_min_score_accepts_percentage_and_ratio_inputs() -> None:
    assert parse_min_score("80") == 0.8
    assert parse_min_score("0.75") == 0.75


def test_run_github_action_passes_requested_mode_to_verification(monkeypatch, tmp_path) -> None:
    scenario = Scenario(
        method="GET",
        path="/health",
        request=RequestExample(method="GET", path="/health"),
        expected_response=ResponseExample(status_code=200, json={"status": "ok"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[scenario],
        replay_results=[],
        replay_traces=[],
        property_results=[],
    )
    captured: dict[str, str] = {}

    def fake_run_verification(root, mode="local"):
        captured["root"] = str(root)
        captured["mode"] = mode
        return result

    monkeypatch.setattr("litmus.github_action.report.run_verification", fake_run_verification)
    monkeypatch.setattr(
        "litmus.github_action.report.save_replay_trace_records",
        lambda *_args, **_kwargs: None,
    )

    report = run_github_action(
        workspace=tmp_path,
        mode="ci",
        min_score=parse_min_score("80"),
        include_comment=False,
        output_path=None,
        summary_path=None,
        comment_path=tmp_path / "litmus-pr-comment.md",
    )

    assert captured["root"] == str(tmp_path)
    assert captured["mode"] == "ci"
    assert report.verdict == "fail"
