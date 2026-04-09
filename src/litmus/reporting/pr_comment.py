from __future__ import annotations

from collections import Counter, defaultdict
import json
from typing import Any

from litmus.compatibility import compatibility_report_from_result, render_compatibility_markdown_lines
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.trace import boundary_coverage_from_result
from litmus.replay.differential import ReplayClassification
from litmus.reporting.confidence import calculate_confidence_score
from litmus.runs.summary import VerificationProjection
from litmus.surface import GROUNDED_ALPHA_SURFACE_SHORT_LABEL


def render_pr_comment(result) -> str:
    projection = VerificationProjection.from_result(result)
    confidence = calculate_confidence_score(result.replay_results, result.property_results)

    lines = [
        "## Litmus Verification (Grounded Alpha)",
        "",
        f"Surface: `{GROUNDED_ALPHA_SURFACE_SHORT_LABEL}`",
        f"Confidence score: `{confidence:.2f}`",
        f"App: `{projection.app_reference}`",
        "",
        "### Decision",
        f"- Verdict: `{projection.verification_verdict['decision']}`",
        f"- Merge recommendation: `{projection.policy_evaluation['merge_recommendation']}`",
        _risk_summary_line(projection),
        f"- Summary: {projection.verification_verdict['summary']}",
        _policy_failing_checks_line(projection),
        _policy_warning_checks_line(projection),
        _evidence_summary_line(projection),
        "",
        "### Affected Endpoints",
    ]
    lines.extend(f"- `{endpoint}`" for endpoint in _affected_endpoints(result))
    lines.extend(
        [
            "",
            "### Layer Results",
            "- Invariants: "
            f"total={projection.invariants['total']} "
            f"confirmed={projection.invariants['confirmed']} "
            f"suggested={projection.invariants['suggested']}",
            "- Replay: "
            f"unchanged={projection.replay['unchanged']} "
            f"breaking={projection.replay['breaking_change']} "
            f"benign={projection.replay['benign_change']} "
            f"improvement={projection.replay['improvement']}",
            "- Properties: "
            f"passed={projection.properties['passed']} "
            f"failed={projection.properties['failed']} "
            f"skipped={projection.properties['skipped']}",
            "- DST coverage: "
            + " ".join(_boundary_coverage_tokens(result)),
            "",
            "### Compatibility",
            *render_compatibility_markdown_lines(compatibility_report_from_result(result)),
            "",
            "### Failing Seeds",
        ]
    )

    failing_seed_lines = _failing_seed_lines(result)
    if failing_seed_lines:
        lines.extend(failing_seed_lines)
    else:
        lines.append("- No failing seeds recorded.")

    pending_review_lines = _pending_review_lines(result)
    if pending_review_lines:
        lines.extend(
            [
                "",
                "### Pending Invariant Review",
                *pending_review_lines,
            ]
        )

    explanation_lines = _explanation_lines(result)
    if explanation_lines:
        lines.extend(
            [
                "",
                "### What Went Wrong",
                *explanation_lines,
            ]
        )
    elif not pending_review_lines:
        lines.extend(
            [
                "",
                "### What Went Wrong",
            ]
        )
        lines.append("- No breaking replay or property failures detected.")

    return "\n".join(lines)


def _affected_endpoints(result) -> list[str]:
    endpoints = {
        f"{scenario.method} {scenario.path}"
        for scenario in result.scenarios
    }
    for invariant in result.invariants:
        request = invariant.request
        if request is None or request.method is None or request.path is None:
            continue
        endpoints.add(f"{request.method.upper()} {request.path}")
    for property_result in result.property_results:
        request = property_result.invariant.request
        if request is None or request.method is None or request.path is None:
            continue
        endpoints.add(f"{request.method.upper()} {request.path}")
    return sorted(endpoints)


def _failing_seed_lines(result) -> list[str]:
    trace_records_by_key: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    for replay_trace in result.replay_traces:
        trace_records_by_key[
            _replay_identity_key(
                method=replay_trace.method,
                path=replay_trace.path,
                payload=replay_trace.request_payload,
            )
        ].append(replay_trace)
    lines: list[str] = []
    for replay_result in result.replay_results:
        if replay_result.classification is not ReplayClassification.BREAKING_CHANGE:
            continue

        replay_traces = trace_records_by_key.get(
            _replay_identity_key(
                method=replay_result.scenario.method,
                path=replay_result.scenario.path,
                payload=replay_result.scenario.request.payload,
            )
        )
        if not replay_traces:
            lines.append(
                "- "
                f"Replay trace missing for `{replay_result.scenario.method} {replay_result.scenario.path}`; "
                "rerun `litmus verify` before replaying."
            )
            continue
        replay_trace = replay_traces.pop(0)

        lines.append(
            "- "
            f"`{replay_trace.seed}` on `{replay_result.scenario.method} {replay_result.scenario.path}` "
            f"-> `litmus replay {replay_trace.seed}`"
        )
    return lines


def _explanation_lines(result) -> list[str]:
    lines: list[str] = []
    for replay_result in result.replay_results:
        if replay_result.classification is not ReplayClassification.BREAKING_CHANGE:
            continue
        lines.append(_replay_explanation(replay_result))

    for property_result in result.property_results:
        if property_result.status is not PropertyCheckStatus.FAILED:
            continue
        lines.append(_property_explanation(property_result))

    return lines


def _pending_review_lines(result) -> list[str]:
    return [
        _suggested_invariant_explanation(invariant)
        for invariant in result.invariants
        if invariant.is_pending_suggestion()
    ]


def _replay_explanation(replay_result) -> str:
    endpoint = f"{replay_result.scenario.method} {replay_result.scenario.path}"
    status_before, status_after = replay_result.diff.get(
        "status_code",
        (
            replay_result.baseline_response.status_code,
            replay_result.changed_response.status_code,
        ),
    )
    body_diff = replay_result.diff.get("body")

    if body_diff is None:
        return f"- Replay regression on `{endpoint}`: status `{status_before}` -> `{status_after}`."

    body_before, body_after = body_diff
    return (
        f"- Replay regression on `{endpoint}`: status `{status_before}` -> `{status_after}`, "
        f"body `{_format_value(body_before)}` -> `{_format_value(body_after)}`."
    )


def _property_explanation(property_result) -> str:
    request = property_result.failing_request
    if request is None:
        return f"- Property invariant `{property_result.invariant.name}` failed."

    method = request.method or "UNKNOWN"
    path = request.path or "/"
    payload = _format_value(request.payload)
    return (
        f"- Property invariant `{property_result.invariant.name}` failed for "
        f"`{method} {path}` with request `{payload}`."
    )


def _suggested_invariant_explanation(invariant) -> str:
    request = invariant.request
    if request is None or request.method is None or request.path is None:
        if invariant.reasoning is None:
            return f"- Pending review for suggested invariant `{invariant.name}`."
        return f"- Pending review for suggested invariant `{invariant.name}`: {invariant.reasoning}"

    endpoint = f"{request.method.upper()} {request.path}"
    if invariant.reasoning is None:
        return f"- Pending review for suggested invariant `{invariant.name}` on `{endpoint}`."
    return f"- Pending review for suggested invariant `{invariant.name}` on `{endpoint}`: {invariant.reasoning}"


def _format_value(value) -> str:
    return json.dumps(value, sort_keys=True)


def _replay_identity_key(*, method: str, path: str, payload: dict[str, Any] | None) -> tuple[str, str, str]:
    return (
        method.upper(),
        path,
        json.dumps(payload, sort_keys=True) if payload is not None else "null",
    )


def _boundary_coverage_tokens(result) -> list[str]:
    coverage = boundary_coverage_from_result(result)
    return [
        f"{boundary}={_coverage_token(snapshot)}"
        for boundary, snapshot in coverage.items()
        if snapshot.detected or snapshot.intercepted or snapshot.simulated or snapshot.faulted or snapshot.unsupported
    ]


def _coverage_token(snapshot) -> str:
    if snapshot.unsupported:
        return "unsupported"
    if snapshot.faulted:
        return "faulted"
    if snapshot.simulated:
        return "simulated"
    if snapshot.intercepted:
        return "intercepted"
    if snapshot.detected:
        return "detected"
    return "none"


def _risk_summary_line(projection: VerificationProjection) -> str:
    risk = projection.risk_assessment
    if risk["risk_classes"]:
        rendered_classes = ", ".join(f"`{risk_class}`" for risk_class in risk["risk_classes"])
        return f"- Risk: `{risk['level']}` ({rendered_classes})"
    return f"- Risk: `{risk['level']}`"


def _policy_failing_checks_line(projection: VerificationProjection) -> str:
    failing_checks = projection.policy_evaluation["failing_checks"]
    if not failing_checks:
        return "- Failed policy checks: none"
    rendered = ", ".join(f"`{check}`" for check in failing_checks)
    return f"- Failed policy checks: {rendered}"


def _policy_warning_checks_line(projection: VerificationProjection) -> str:
    warning_checks = projection.policy_evaluation["warning_checks"]
    if not warning_checks:
        return "- Warning policy checks: none"
    rendered = ", ".join(f"`{check}`" for check in warning_checks)
    return f"- Warning policy checks: {rendered}"


def _evidence_summary_line(projection: VerificationProjection) -> str:
    evidence = projection.evidence
    return (
        "- Evidence: "
        f"signals={evidence['total_signals']} "
        f"detected_boundaries={evidence['detected_boundary_count']} "
        f"unsupported_gaps={evidence['unsupported_gap_count']} "
        f"pending_review={evidence['pending_review_count']}"
    )
