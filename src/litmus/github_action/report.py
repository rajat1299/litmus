from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from litmus.dst.engine import run_verification
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.replay.trace import save_replay_trace_records
from litmus.reporting.confidence import calculate_confidence_score
from litmus.reporting.console import render_verification_summary
from litmus.reporting.pr_comment import render_pr_comment


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
    include_comment = os.getenv("LITMUS_COMMENT", "true").strip().lower() != "false"
    min_score = parse_min_score(os.getenv("LITMUS_MIN_SCORE"))

    result = run_verification(workspace)
    save_replay_trace_records(workspace, result.replay_traces)

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
    raise SystemExit(1 if report.should_fail else 0)


def _optional_path(raw_value: str | None) -> Path | None:
    if raw_value is None or not raw_value.strip():
        return None
    return Path(raw_value)


if __name__ == "__main__":
    main()
