from __future__ import annotations

from litmus.compatibility import CompatibilityReport, render_compatibility_lines
from litmus.replay.trace import boundary_coverage_from_result
from litmus.runs.summary import VerificationProjection
from litmus.surface import GROUNDED_ALPHA_SURFACE_LABEL


def render_verification_summary(result) -> str:
    projection = VerificationProjection.from_result(result)

    lines = [
        "Litmus verify",
        f"Surface: {GROUNDED_ALPHA_SURFACE_LABEL}",
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
        _performance_summary_line(projection),
        "Launch budgets: "
        f"replay_seeds/scenario={projection.performance['replay_seeds_per_scenario']} "
        f"property_examples={projection.performance['property_max_examples']}",
        _budget_policy_line(projection),
        f"Confidence: {projection.confidence:.2f}",
    ]
    coverage_lines = _boundary_coverage_lines(result)
    if coverage_lines:
        lines.append("DST coverage:")
        lines.extend(coverage_lines)
    compatibility_lines = _compatibility_lines(projection)
    if compatibility_lines:
        lines.append("Compatibility:")
        lines.extend(compatibility_lines)
    suggestion_lines = _pending_review_lines(result)
    if suggestion_lines:
        lines.append("Pending invariant review:")
        lines.extend(suggestion_lines)
    return "\n".join(lines)


def _pending_review_lines(result) -> list[str]:
    lines: list[str] = []
    for invariant in result.invariants:
        if not invariant.is_pending_suggestion():
            continue
        if invariant.reasoning is None:
            lines.append(f"- {invariant.name}")
            continue
        lines.append(f"- {invariant.name}: {invariant.reasoning}")
    return lines


def _performance_summary_line(projection: VerificationProjection) -> str:
    performance = projection.performance
    if not performance["measured"]:
        return (
            "Performance: "
            f"elapsed=unmeasured "
            f"budget<={performance['budget_ms'] / 1000:.2f}s "
            f"mode={performance['mode']} "
            f"profile={performance['fault_profile']} "
            "within_budget=unknown"
        )
    return (
        "Performance: "
        f"elapsed={performance['elapsed_ms'] / 1000:.2f}s "
        f"budget<={performance['budget_ms'] / 1000:.2f}s "
        f"mode={performance['mode']} "
        f"profile={performance['fault_profile']} "
        f"within_budget={'yes' if performance['within_budget'] else 'no'}"
    )


def _budget_policy_line(projection: VerificationProjection) -> str:
    policy = projection.performance["budget_policy"]
    descriptions = {
        "launch_default": "launch-default under-10s path",
        "launch_lighter": "lighter local path",
        "local_deeper_opt_in": "deeper local opt-in path",
        "mcp_local_agent": "local MCP/agent path",
        "watch_local_iteration": "local watch iteration path",
        "ci_deeper": "CI deeper-search path",
    }
    return f"Budget policy: {descriptions[policy]}"


def _boundary_coverage_lines(result) -> list[str]:
    coverage = boundary_coverage_from_result(result)
    return [
        f"- {boundary}: {_format_coverage_state(snapshot)}"
        for boundary, snapshot in coverage.items()
        if snapshot.detected or snapshot.intercepted or snapshot.simulated or snapshot.faulted or snapshot.unsupported
    ]


def _format_coverage_state(snapshot) -> str:
    states: list[str] = []
    if snapshot.unsupported:
        states.append("unsupported")
    if snapshot.detected:
        states.append("detected")
    if snapshot.intercepted:
        states.append("intercepted")
    if snapshot.simulated:
        states.append("simulated")
    if snapshot.faulted:
        states.append("faulted")
    return ", ".join(states)


def _compatibility_lines(projection: VerificationProjection) -> list[str]:
    report = CompatibilityReport.from_dict(projection.compatibility)
    return render_compatibility_lines(report)
