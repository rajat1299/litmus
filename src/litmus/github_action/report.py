from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from litmus.decisioning import MergeRecommendation, evaluate_verification_result
from litmus.dst.engine import run_verification
from litmus.errors import LitmusUserError, VerificationModeError
from litmus.github_action.publish import publish_pr_comment
from litmus.reporting.confidence import calculate_confidence_score
from litmus.reporting.console import render_verification_summary
from litmus.reporting.pr_comment import render_pr_comment
from litmus.runs import RunMode, record_verification_run


@dataclass(slots=True)
class ActionReport:
    confidence: float
    action_status: str
    verdict: str
    decision: str | None
    merge_recommendation: str | None
    should_fail: bool
    summary: str
    comment: str
    include_comment: bool


@dataclass(slots=True)
class ActionOutputPaths:
    output_path: Path | None
    summary_path: Path | None
    comment_path: Path | None


@dataclass(slots=True)
class GitHubCommentContext:
    token: str
    repository: str
    event_path: Path
    api_url: str = "https://api.github.com"


def parse_min_score(value: str | None) -> float:
    if value is None or not value.strip():
        return 0.0

    numeric = float(value)
    if numeric > 1:
        numeric = numeric / 100.0
    return max(0.0, min(numeric, 1.0))


def build_action_report(
    result,
    *,
    min_score: float,
    include_comment: bool,
) -> ActionReport:
    confidence = calculate_confidence_score(result.replay_results, result.property_results)
    decision_bundle = getattr(result, "decision_bundle", None) or evaluate_verification_result(result)
    policy_requires_failure = (
        decision_bundle.policy.merge_recommendation is not MergeRecommendation.ALLOW
    )
    should_fail = policy_requires_failure or confidence < min_score

    return ActionReport(
        confidence=confidence,
        action_status="verified",
        verdict="fail" if should_fail else "pass",
        decision=decision_bundle.verdict.decision.value,
        merge_recommendation=decision_bundle.policy.merge_recommendation.value,
        should_fail=should_fail,
        summary=render_verification_summary(result),
        comment=render_pr_comment(result),
        include_comment=include_comment,
    )


def write_action_report(
    report: ActionReport,
    *,
    output_path: Path | None,
    summary_path: Path | None,
    comment_path: Path | None,
) -> None:
    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_content = report.summary
        if report.include_comment:
            summary_content = f"{summary_content}\n\n{report.comment}"
        summary_path.write_text(summary_content + "\n", encoding="utf-8")

    written_comment_path = ""
    if report.include_comment and comment_path is not None:
        comment_path.parent.mkdir(parents=True, exist_ok=True)
        comment_path.write_text(report.comment + "\n", encoding="utf-8")
        written_comment_path = str(comment_path)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_lines = [
            f"confidence={report.confidence:.2f}",
            f"action-status={report.action_status}",
            f"verdict={report.verdict}",
        ]
        if report.decision is not None:
            output_lines.append(f"decision={report.decision}")
        if report.merge_recommendation is not None:
            output_lines.append(f"merge-recommendation={report.merge_recommendation}")
        output_lines.append(f"comment-path={written_comment_path}")
        output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


def build_error_action_report(error: LitmusUserError) -> ActionReport:
    return ActionReport(
        confidence=0.0,
        action_status="verification_error",
        verdict="fail",
        decision=None,
        merge_recommendation=None,
        should_fail=True,
        summary=f"Litmus verify\nError: {error}",
        comment="",
        include_comment=False,
    )


def main() -> None:
    workspace = Path(os.getenv("LITMUS_WORKSPACE", Path.cwd()))
    outputs = ActionOutputPaths(
        output_path=_optional_path(os.getenv("GITHUB_OUTPUT")),
        summary_path=_optional_path(os.getenv("GITHUB_STEP_SUMMARY")),
        comment_path=Path(
            os.getenv("LITMUS_COMMENT_PATH", str(workspace / ".litmus" / "pr-comment.md"))
        ),
    )
    include_comment = os.getenv("LITMUS_COMMENT", "true").strip().lower() != "false"
    min_score = parse_min_score(os.getenv("LITMUS_MIN_SCORE"))
    decision_policy = _optional_string(os.getenv("LITMUS_DECISION_POLICY"))
    github = _github_comment_context()

    try:
        mode = _parse_run_mode(os.getenv("LITMUS_MODE", RunMode.LOCAL.value))
        report = run_github_action(
            workspace=workspace,
            mode=mode,
            decision_policy=decision_policy,
            min_score=min_score,
            include_comment=include_comment,
            outputs=outputs,
        )
    except LitmusUserError as exc:
        report = build_error_action_report(exc)
        write_action_report(
            report,
            output_path=outputs.output_path,
            summary_path=outputs.summary_path,
            comment_path=outputs.comment_path,
        )
        raise SystemExit(1) from None
    publish_action_comment(report, include_comment=include_comment, github=github)
    raise SystemExit(1 if report.should_fail else 0)


def _optional_path(raw_value: str | None) -> Path | None:
    if raw_value is None or not raw_value.strip():
        return None
    return Path(raw_value)


def _optional_string(raw_value: str | None) -> str | None:
    if raw_value is None or not raw_value.strip():
        return None
    return raw_value


def _github_comment_context() -> GitHubCommentContext | None:
    token = _optional_string(os.getenv("LITMUS_GITHUB_TOKEN"))
    repository = _optional_string(os.getenv("GITHUB_REPOSITORY"))
    event_path = _optional_path(os.getenv("GITHUB_EVENT_PATH"))
    if token is None or repository is None or event_path is None:
        return None
    return GitHubCommentContext(
        token=token,
        repository=repository,
        event_path=event_path,
        api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
    )


def run_github_action(
    *,
    workspace: Path,
    mode: RunMode,
    decision_policy: str | None = None,
    min_score: float,
    include_comment: bool,
    outputs: ActionOutputPaths,
) -> ActionReport:
    if decision_policy is None:
        result = run_verification(workspace, mode=mode)
    else:
        result = run_verification(workspace, mode=mode, decision_policy=decision_policy)
    record_verification_run(workspace, result, mode=mode)

    report = build_action_report(
        result,
        min_score=min_score,
        include_comment=include_comment,
    )
    write_action_report(
        report,
        output_path=outputs.output_path,
        summary_path=outputs.summary_path,
        comment_path=outputs.comment_path,
    )
    return report


def publish_action_comment(
    report: ActionReport,
    *,
    include_comment: bool,
    github: GitHubCommentContext | None,
) -> None:
    if not include_comment or github is None:
        return
    publish_pr_comment(
        api_url=github.api_url,
        repository=github.repository,
        event_path=github.event_path,
        token=github.token,
        comment=report.comment,
    )


def _parse_run_mode(raw_value: str) -> RunMode:
    normalized_value = raw_value.strip().lower()
    if normalized_value == RunMode.CI.value:
        return RunMode.CI
    if normalized_value == RunMode.LOCAL.value:
        return RunMode.LOCAL
    if normalized_value == RunMode.MCP.value:
        return RunMode.MCP
    if normalized_value == RunMode.WATCH.value:
        return RunMode.WATCH
    raise VerificationModeError(f"unsupported verification mode: {raw_value}")


if __name__ == "__main__":
    main()
