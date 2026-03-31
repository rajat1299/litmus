from __future__ import annotations

from collections import Counter, defaultdict
import json
from typing import Any

from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.reporting.confidence import calculate_confidence_score


def render_pr_comment(result) -> str:
    replay_counts = Counter(replay.classification for replay in result.replay_results)
    property_counts = Counter(property_result.status for property_result in result.property_results)
    confidence = calculate_confidence_score(result.replay_results, result.property_results)

    lines = [
        "## Litmus Verification",
        "",
        f"Confidence score: `{confidence:.2f}`",
        f"App: `{result.app_reference}`",
        "",
        "### Affected Endpoints",
    ]
    lines.extend(f"- `{endpoint}`" for endpoint in _affected_endpoints(result))
    lines.extend(
        [
            "",
            "### Layer Results",
            "- Replay: "
            f"unchanged={replay_counts[ReplayClassification.UNCHANGED]} "
            f"breaking={replay_counts[ReplayClassification.BREAKING_CHANGE]} "
            f"benign={replay_counts[ReplayClassification.BENIGN_CHANGE]} "
            f"improvement={replay_counts[ReplayClassification.IMPROVEMENT]}",
            "- Properties: "
            f"passed={property_counts[PropertyCheckStatus.PASSED]} "
            f"failed={property_counts[PropertyCheckStatus.FAILED]} "
            f"skipped={property_counts[PropertyCheckStatus.SKIPPED]}",
            "",
            "### Failing Seeds",
        ]
    )

    failing_seed_lines = _failing_seed_lines(result)
    if failing_seed_lines:
        lines.extend(failing_seed_lines)
    else:
        lines.append("- No failing seeds recorded.")

    lines.extend(
        [
            "",
            "### What Went Wrong",
        ]
    )
    explanation_lines = _explanation_lines(result)
    if explanation_lines:
        lines.extend(explanation_lines)
    else:
        lines.append("- No breaking replay or property failures detected.")

    return "\n".join(lines)


def _affected_endpoints(result) -> list[str]:
    endpoints = {
        f"{scenario.method} {scenario.path}"
        for scenario in result.scenarios
    }
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


def _format_value(value) -> str:
    return json.dumps(value, sort_keys=True)


def _replay_identity_key(*, method: str, path: str, payload: dict[str, Any] | None) -> tuple[str, str, str]:
    return (
        method.upper(),
        path,
        json.dumps(payload, sort_keys=True) if payload is not None else "null",
    )
