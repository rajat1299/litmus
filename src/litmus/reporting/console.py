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
        f"Decision: {projection.verification_verdict['decision']}",
        f"Merge recommendation: {projection.policy_evaluation['merge_recommendation']}",
        _risk_summary_line(projection),
        _evidence_summary_line(projection),
        _policy_summary_line(projection),
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
        _search_budget_line(projection),
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
            f"strategy={performance['search_strategy']} "
            "within_budget=unknown"
        )
    return (
        "Performance: "
        f"elapsed={performance['elapsed_ms'] / 1000:.2f}s "
        f"budget<={performance['budget_ms'] / 1000:.2f}s "
        f"mode={performance['mode']} "
        f"profile={performance['fault_profile']} "
        f"strategy={performance['search_strategy']} "
        f"within_budget={'yes' if performance['within_budget'] else 'no'}"
    )


def _risk_summary_line(projection: VerificationProjection) -> str:
    risk = projection.risk_assessment
    classes = ",".join(risk["risk_classes"]) if risk["risk_classes"] else "none"
    return f"Risk: {risk['level']} classes={classes}"


def _evidence_summary_line(projection: VerificationProjection) -> str:
    evidence = projection.evidence
    return (
        "Evidence: "
        f"signals={evidence['total_signals']} "
        f"detected_boundaries={evidence['detected_boundary_count']} "
        f"unsupported_gaps={evidence['unsupported_gap_count']} "
        f"pending_review={evidence['pending_review_count']}"
    )


def _policy_summary_line(projection: VerificationProjection) -> str:
    policy = projection.policy_evaluation
    failing = ",".join(policy["failing_checks"]) if policy["failing_checks"] else "none"
    warnings = ",".join(policy["warning_checks"]) if policy["warning_checks"] else "none"
    return f"Policy: {policy['policy_name']} failing={failing} warnings={warnings}"


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


def _search_budget_line(projection: VerificationProjection) -> str:
    search_budget = projection.performance["search_budget"]
    targets = search_budget["unique_selected_targets"]
    fault_kinds = search_budget["unique_planned_fault_kinds"]
    rendered_targets = "none" if not targets else ",".join(targets)
    rendered_fault_kinds = "none" if not fault_kinds else ",".join(fault_kinds)
    return (
        "Search budget: "
        f"requested_total={search_budget['requested_total_replay_seeds']} "
        f"allocated_total={search_budget['allocated_total_replay_seeds']} "
        f"executed={search_budget['executed_replays']} "
        f"single_target={search_budget['target_single_scenarios']} "
        f"kind_diverse={search_budget['kind_diverse_scenarios']} "
        f"priority_multi={search_budget['multi_target_priority_scenarios']} "
        f"frontier_capped={search_budget['frontier_capped_scenarios']} "
        f"redistributed={search_budget['redistributed_scenarios']} "
        f"no_boundary={search_budget['no_boundary_scenarios']} "
        f"targets={rendered_targets} "
        f"kinds={rendered_fault_kinds}"
    )


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
