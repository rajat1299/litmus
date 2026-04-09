from __future__ import annotations

from pathlib import Path

import pytest

from litmus.dst.engine import VerificationResult
from litmus.dst.runtime import TraceEvent
from litmus.discovery.app import AppLoadError
from litmus.invariants.models import RequestExample, ResponseExample
from litmus.replay.differential import DifferentialReplayResult, ReplayClassification
from litmus.replay.trace import ReplayTraceRecord
from litmus.github_action.report import (
    ActionOutputPaths,
    GitHubCommentContext,
    build_action_report,
    build_error_action_report,
    main,
    parse_min_score,
    publish_action_comment,
    run_github_action,
    write_action_report,
)
from litmus.runs import RunMode
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
    assert "Suggested invariants: 0" in report.summary
    assert f"comment-path={comment_path}" in output_path.read_text(encoding="utf-8")
    assert "confidence=0.00" in output_path.read_text(encoding="utf-8")
    assert "action-status=verified" in output_path.read_text(encoding="utf-8")
    assert "decision=unsafe" in output_path.read_text(encoding="utf-8")
    assert "merge-recommendation=block" in output_path.read_text(encoding="utf-8")
    assert "verdict=fail" in output_path.read_text(encoding="utf-8")
    assert "## Litmus Verification" in comment_path.read_text(encoding="utf-8")
    assert "### Decision" in comment_path.read_text(encoding="utf-8")
    assert "### Affected Endpoints" in summary_path.read_text(encoding="utf-8")


def test_parse_min_score_accepts_percentage_and_ratio_inputs() -> None:
    assert parse_min_score("80") == 0.8
    assert parse_min_score("0.75") == 0.75


def test_build_action_report_fails_review_required_verification_runs() -> None:
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
                changed_response=ResponseExample(status_code=200, json={"status": "charged"}),
                classification=ReplayClassification.UNCHANGED,
            )
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:1",
                seed_value=1,
                app_reference="service.app:app",
                method="POST",
                path="/payments/charge",
                request_payload={"amount": 100},
                baseline_status_code=200,
                baseline_body={"status": "charged"},
                trace=[
                    TraceEvent(kind="boundary_detected", metadata={"boundary": "redis"}),
                    TraceEvent(
                        kind="boundary_unsupported",
                        metadata={
                            "boundary": "redis",
                            "detail": "Unsupported constructor or type import in loaded app modules.",
                        },
                    ),
                ],
            )
        ],
        property_results=[],
    )

    report = build_action_report(result, min_score=parse_min_score("0"), include_comment=False)

    assert report.action_status == "verified"
    assert report.decision == "needs_deeper_verification"
    assert report.merge_recommendation == "review_required"
    assert report.verdict == "fail"
    assert report.should_fail is True


def test_build_error_action_report_uses_separate_action_status_for_execution_failures() -> None:
    report = build_error_action_report(
        AppLoadError("service.app:missing_app", "Missing attribute 'missing_app' on module 'service.app'.")
    )

    assert report.action_status == "verification_error"
    assert report.decision is None
    assert report.merge_recommendation is None
    assert report.verdict == "fail"
    assert report.should_fail is True


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

    def fake_run_verification(root, mode=RunMode.LOCAL):
        captured["root"] = str(root)
        captured["mode"] = mode
        return result

    monkeypatch.setattr("litmus.github_action.report.run_verification", fake_run_verification)
    captured_recording: dict[str, object] = {}
    monkeypatch.setattr(
        "litmus.github_action.report.record_verification_run",
        lambda workspace, result, *, mode: captured_recording.update(
            {"workspace": workspace, "mode": mode, "result": result}
        ),
    )
    monkeypatch.setattr(
        "litmus.github_action.report.publish_pr_comment",
        lambda **_kwargs: None,
    )

    report = run_github_action(
        workspace=tmp_path,
        mode=RunMode.CI,
        min_score=parse_min_score("80"),
        include_comment=False,
        outputs=ActionOutputPaths(
            output_path=None,
            summary_path=None,
            comment_path=tmp_path / "litmus-pr-comment.md",
        ),
    )

    assert captured["root"] == str(tmp_path)
    assert captured["mode"] is RunMode.CI
    assert captured_recording["workspace"] == tmp_path
    assert str(captured_recording["mode"]) == "RunMode.CI"
    assert report.verdict == "fail"


def test_run_github_action_records_requested_non_ci_mode(monkeypatch, tmp_path) -> None:
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[],
        replay_results=[],
        replay_traces=[],
        property_results=[],
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "litmus.github_action.report.run_verification",
        lambda *_args, **_kwargs: result,
    )
    monkeypatch.setattr(
        "litmus.github_action.report.record_verification_run",
        lambda workspace, recorded_result, *, mode: captured.update(
            {"workspace": workspace, "result": recorded_result, "mode": mode}
        ),
    )

    run_github_action(
        workspace=tmp_path,
        mode=RunMode.LOCAL,
        min_score=parse_min_score("80"),
        include_comment=False,
        outputs=ActionOutputPaths(
            output_path=None,
            summary_path=None,
            comment_path=tmp_path / "litmus-pr-comment.md",
        ),
    )

    assert captured["workspace"] == tmp_path
    assert captured["result"] is result
    assert captured["mode"] is RunMode.LOCAL


def test_run_github_action_passes_decision_policy_override_to_verification(monkeypatch, tmp_path) -> None:
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[],
        replay_results=[],
        replay_traces=[],
        property_results=[],
        decision_policy="strict_local_v1",
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "litmus.github_action.report.run_verification",
        lambda workspace, *, mode, decision_policy=None: captured.update(
            {"workspace": workspace, "mode": mode, "decision_policy": decision_policy}
        )
        or result,
    )
    monkeypatch.setattr(
        "litmus.github_action.report.record_verification_run",
        lambda *_args, **_kwargs: None,
    )

    report = run_github_action(
        workspace=tmp_path,
        mode=RunMode.CI,
        decision_policy="strict_local_v1",
        min_score=parse_min_score("0"),
        include_comment=False,
        outputs=ActionOutputPaths(
            output_path=None,
            summary_path=None,
            comment_path=tmp_path / "litmus-pr-comment.md",
        ),
    )

    assert captured["workspace"] == tmp_path
    assert captured["mode"] is RunMode.CI
    assert captured["decision_policy"] == "strict_local_v1"
    assert report.merge_recommendation == "block"


def test_publish_action_comment_publishes_comment_when_github_context_exists(monkeypatch, tmp_path) -> None:
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
    captured: dict[str, object] = {}
    event_path = tmp_path / "event.json"
    event_path.write_text('{"pull_request": {"number": 5}}', encoding="utf-8")

    def fake_publish_pr_comment(**kwargs):
        captured.update(kwargs)
        return "https://github.example/comment/5"

    monkeypatch.setattr("litmus.github_action.report.publish_pr_comment", fake_publish_pr_comment)

    report = build_action_report(
        result,
        min_score=parse_min_score("80"),
        include_comment=True,
    )
    publish_action_comment(
        report,
        include_comment=True,
        github=GitHubCommentContext(
            token="token-123",
            repository="acme/litmus",
            event_path=event_path,
        ),
    )

    assert captured["repository"] == "acme/litmus"
    assert captured["token"] == "token-123"
    assert captured["event_path"] == event_path
    assert "## Litmus Verification" in str(captured["comment"])


def test_main_writes_failed_action_report_for_litmus_boundary_error(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "github-output.txt"
    summary_path = tmp_path / "step-summary.md"
    comment_path = tmp_path / "litmus-pr-comment.md"

    monkeypatch.setenv("LITMUS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setenv("LITMUS_COMMENT_PATH", str(comment_path))
    monkeypatch.setenv("LITMUS_COMMENT", "true")
    monkeypatch.setenv("LITMUS_MODE", "ci")
    monkeypatch.delenv("LITMUS_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.setattr(
        "litmus.github_action.report.run_github_action",
        lambda **_kwargs: (_ for _ in ()).throw(
            AppLoadError("service.app:missing_app", "Missing attribute 'missing_app' on module 'service.app'.")
        ),
    )
    published: list[object] = []
    monkeypatch.setattr(
        "litmus.github_action.report.publish_pr_comment",
        lambda **_kwargs: published.append(object()),
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert published == []
    assert "confidence=0.00" in output_path.read_text(encoding="utf-8")
    assert "action-status=verification_error" in output_path.read_text(encoding="utf-8")
    assert "verdict=fail" in output_path.read_text(encoding="utf-8")
    assert "decision=" not in output_path.read_text(encoding="utf-8")
    assert "merge-recommendation=" not in output_path.read_text(encoding="utf-8")
    assert "comment-path=" in output_path.read_text(encoding="utf-8")
    assert "Litmus verify" in summary_path.read_text(encoding="utf-8")
    assert "Could not load ASGI app 'service.app:missing_app'" in summary_path.read_text(encoding="utf-8")
    assert not comment_path.exists()


def test_main_writes_failed_action_report_for_invalid_litmus_mode(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "github-output.txt"
    summary_path = tmp_path / "step-summary.md"
    comment_path = tmp_path / "litmus-pr-comment.md"

    monkeypatch.setenv("LITMUS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setenv("LITMUS_COMMENT_PATH", str(comment_path))
    monkeypatch.setenv("LITMUS_COMMENT", "true")
    monkeypatch.setenv("LITMUS_MODE", "bogus")
    monkeypatch.delenv("LITMUS_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "confidence=0.00" in output_path.read_text(encoding="utf-8")
    assert "action-status=verification_error" in output_path.read_text(encoding="utf-8")
    assert "verdict=fail" in output_path.read_text(encoding="utf-8")
    assert "decision=" not in output_path.read_text(encoding="utf-8")
    assert "merge-recommendation=" not in output_path.read_text(encoding="utf-8")
    assert "comment-path=" in output_path.read_text(encoding="utf-8")
    assert "Litmus verify" in summary_path.read_text(encoding="utf-8")
    assert "unsupported verification mode: bogus" in summary_path.read_text(encoding="utf-8")
    assert not comment_path.exists()


def test_main_passes_decision_policy_override_to_github_action(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "github-output.txt"
    summary_path = tmp_path / "step-summary.md"
    comment_path = tmp_path / "litmus-pr-comment.md"
    captured: dict[str, object] = {}

    monkeypatch.setenv("LITMUS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setenv("LITMUS_COMMENT_PATH", str(comment_path))
    monkeypatch.setenv("LITMUS_COMMENT", "false")
    monkeypatch.setenv("LITMUS_MODE", "ci")
    monkeypatch.setenv("LITMUS_DECISION_POLICY", "strict_local_v1")
    monkeypatch.delenv("LITMUS_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.setattr(
        "litmus.github_action.report.run_github_action",
        lambda **kwargs: captured.update(kwargs)
        or build_action_report(
            VerificationResult(
                app_reference="service.app:app",
                routes=[],
                invariants=[],
                scenarios=[],
                replay_results=[],
                replay_traces=[],
                property_results=[],
                decision_policy="strict_local_v1",
            ),
            min_score=0.0,
            include_comment=False,
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert captured["decision_policy"] == "strict_local_v1"
