from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from litmus.dst.engine import run_verification
from litmus.github_action.publish import publish_pr_comment
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.reporting.confidence import calculate_confidence_score
from litmus.reporting.console import render_verification_summary
from litmus.reporting.pr_comment import render_pr_comment
from litmus.runs import RunMode, record_verification_run


@dataclass(slots=True)
class ActionReport:
    confidence: float
    verdict: str
    should_fail: bool
    summary: str
    comment: str
    include_comment: bool


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
    has_breaking_replay = any(
        replay.classification is ReplayClassification.BREAKING_CHANGE
        for replay in result.replay_results
    )
    has_failed_property = any(
        property_result.status is PropertyCheckStatus.FAILED
        for property_result in result.property_results
    )
    should_fail = has_breaking_replay or has_failed_property or confidence < min_score

    return ActionReport(
        confidence=confidence,
        verdict="fail" if should_fail else "pass",
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
        output_path.write_text(
            "\n".join(
                [
                    f"confidence={report.confidence:.2f}",
                    f"verdict={report.verdict}",
                    f"comment-path={written_comment_path}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )


def main() -> None:
    workspace = Path(os.getenv("LITMUS_WORKSPACE", Path.cwd()))
    output_path = _optional_path(os.getenv("GITHUB_OUTPUT"))
    summary_path = _optional_path(os.getenv("GITHUB_STEP_SUMMARY"))
    comment_path = Path(
        os.getenv("LITMUS_COMMENT_PATH", str(workspace / ".litmus" / "pr-comment.md"))
    )
    event_path = _optional_path(os.getenv("GITHUB_EVENT_PATH"))
    mode = os.getenv("LITMUS_MODE", "local")
    include_comment = os.getenv("LITMUS_COMMENT", "true").strip().lower() != "false"
    github_token = _optional_string(os.getenv("LITMUS_GITHUB_TOKEN"))
    repository = _optional_string(os.getenv("GITHUB_REPOSITORY"))
    api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
    min_score = parse_min_score(os.getenv("LITMUS_MIN_SCORE"))

    report = run_github_action(
        workspace=workspace,
        mode=mode,
        min_score=min_score,
        include_comment=include_comment,
        output_path=output_path,
        summary_path=summary_path,
        comment_path=comment_path,
        github_token=github_token,
        repository=repository,
        event_path=event_path,
        api_url=api_url,
    )
    raise SystemExit(1 if report.should_fail else 0)


def _optional_path(raw_value: str | None) -> Path | None:
    if raw_value is None or not raw_value.strip():
        return None
    return Path(raw_value)


def _optional_string(raw_value: str | None) -> str | None:
    if raw_value is None or not raw_value.strip():
        return None
    return raw_value


def run_github_action(
    *,
    workspace: Path,
    mode: str,
    min_score: float,
    include_comment: bool,
    output_path: Path | None,
    summary_path: Path | None,
    comment_path: Path | None,
    github_token: str | None = None,
    repository: str | None = None,
    event_path: Path | None = None,
    api_url: str = "https://api.github.com",
) -> ActionReport:
    result = run_verification(workspace, mode=mode)
    record_verification_run(workspace, result, mode=RunMode.CI)

    report = build_action_report(
        result,
        min_score=min_score,
        include_comment=include_comment,
    )
    write_action_report(
        report,
        output_path=output_path,
        summary_path=summary_path,
        comment_path=comment_path,
    )
    if (
        include_comment
        and github_token is not None
        and repository is not None
        and event_path is not None
    ):
        publish_pr_comment(
            api_url=api_url,
            repository=repository,
            event_path=event_path,
            token=github_token,
            comment=report.comment,
        )
    return report


if __name__ == "__main__":
    main()
