from __future__ import annotations

from litmus.runs.summary import VerificationProjection


def render_verification_summary(result) -> str:
    projection = VerificationProjection.from_result(result)

    lines = [
        "Litmus verify",
        f"App: {projection.app_reference}",
        f"Scope: {projection.scope_label}",
        f"Routes: {projection.routes}",
        f"Invariants: {projection.invariants['total']}",
        f"Confirmed invariants: {projection.invariants['confirmed']}",
        f"Suggested invariants: {projection.invariants['suggested']}",
        f"Scenarios: {projection.scenarios}",
        "Replay: "
        f"unchanged={projection.replay['unchanged']} "
        f"breaking={projection.replay['breaking_change']} "
        f"benign={projection.replay['benign_change']} "
        f"improvement={projection.replay['improvement']}",
        "Properties: "
        f"passed={projection.properties['passed']} "
        f"failed={projection.properties['failed']} "
        f"skipped={projection.properties['skipped']}",
        f"Confidence: {projection.confidence:.2f}",
    ]
    suggestion_lines = _suggestion_lines(result)
    if suggestion_lines:
        lines.append("Suggested actions:")
        lines.extend(suggestion_lines)
    return "\n".join(lines)


def _suggestion_lines(result) -> list[str]:
    lines: list[str] = []
    for invariant in result.invariants:
        if invariant.status.value != "suggested":
            continue
        if invariant.reasoning is None:
            lines.append(f"- {invariant.name}")
            continue
        lines.append(f"- {invariant.name}: {invariant.reasoning}")
    return lines
