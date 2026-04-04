from __future__ import annotations

from typing import Any

from litmus.dst.runtime import TraceEvent
from litmus.replay.differential import ReplayClassification
from litmus.replay.models import ReplayExplanation, ReplayFaultContext, ReplayResponseDetails


def explain_replay(
    *,
    seed: str,
    method: str,
    path: str,
    baseline_status_code: int | None,
    baseline_body: Any,
    current_status_code: int | None,
    current_body: Any,
    classification: ReplayClassification,
    diff: dict[str, tuple[Any, Any]],
    trace: list[TraceEvent],
) -> ReplayExplanation:
    fault_context = _fault_context_from_trace(trace)
    return ReplayExplanation(
        seed=seed,
        method=method,
        path=path,
        classification=classification,
        baseline=ReplayResponseDetails(status_code=baseline_status_code, body=baseline_body),
        current=ReplayResponseDetails(status_code=current_status_code, body=current_body),
        reasons=_reasons_for_replay(classification, diff),
        fault_context=fault_context,
        next_step=_next_step_for_replay(seed, classification, fault_context),
        trace_kinds=[event.kind for event in trace],
    )


def _reasons_for_replay(
    classification: ReplayClassification,
    diff: dict[str, tuple[Any, Any]],
) -> list[str]:
    if not diff:
        return ["Current behavior still matches the baseline response."]

    reasons: list[str] = []

    status_diff = diff.get("status_code")
    if status_diff is not None:
        before, after = status_diff
        if classification is ReplayClassification.BREAKING_CHANGE:
            reasons.append(f"Status code regressed from {before} to {after}.")
        elif classification is ReplayClassification.IMPROVEMENT:
            reasons.append(f"Status code improved from {before} to {after}.")
        else:
            reasons.append(f"Status code changed from {before} to {after}.")

    body_diff = diff.get("body")
    if body_diff is not None:
        before, after = body_diff
        reasons.append(f"Response body changed from {before!r} to {after!r}.")

    return reasons


def _fault_context_from_trace(trace: list[TraceEvent]) -> ReplayFaultContext:
    selected_faults: list[str] = []
    injected_faults: list[str] = []
    boundary_coverage: list[str] = []
    defaulted_responses: list[str] = []
    app_exception: str | None = None

    for event in trace:
        if event.kind == "boundary_detected":
            boundary_coverage.append(f"Detected {event.metadata['boundary']} boundary usage.")
        elif event.kind == "boundary_intercepted":
            boundary_coverage.append(
                f"Intercepted {event.metadata['boundary']} via {event.metadata['supported_shape']}."
            )
        elif event.kind == "boundary_simulated":
            boundary_coverage.append(
                f"Simulated {event.metadata['boundary']} with Litmus state machines."
            )
        elif event.kind == "boundary_unsupported":
            boundary = _display_boundary_name(str(event.metadata["boundary"]))
            boundary_coverage.append(
                f"{boundary} boundary was detected but unsupported: {event.metadata['detail']}."
            )
        elif event.kind == "fault_plan_selected":
            for scheduled_fault in event.metadata.get("schedule", []):
                selected_faults.append(
                    f"Step {scheduled_fault['step']} scheduled {scheduled_fault['kind']} on {scheduled_fault['target']}."
                )
        elif event.kind == "fault_injected":
            target = event.metadata["target"]
            if target == "http":
                injected_faults.append(
                    f"Injected {event.metadata['fault_kind']} on http "
                    f"for {event.metadata['url']} at step {event.metadata['step']}."
                )
            elif target == "redis":
                injected_faults.append(
                    f"Injected {event.metadata['fault_kind']} on redis for "
                    f"{event.metadata['operation']} {event.metadata.get('key', '<unknown>')} "
                    f"at step {event.metadata['step']}."
                )
            elif target == "sqlalchemy":
                table_suffix = (
                    f" {event.metadata['table']}"
                    if event.metadata.get("table") is not None
                    else ""
                )
                injected_faults.append(
                    f"Injected {event.metadata['fault_kind']} on sqlalchemy for "
                    f"{event.metadata['operation']}{table_suffix} at step {event.metadata['step']}."
                )
            else:
                injected_faults.append(
                    f"Injected {event.metadata['fault_kind']} on {target} at step {event.metadata['step']}."
                )
        elif event.kind == "http_response_defaulted":
            defaulted_responses.append(
                f"Used Litmus default JSON response for {event.metadata['method']} "
                f"{event.metadata['url']} at step {event.metadata['step']}."
            )
        elif event.kind == "app_exception":
            app_exception = f"Uncaught {event.metadata['type']}: {event.metadata['message']}"

    return ReplayFaultContext(
        selected_faults=selected_faults,
        injected_faults=injected_faults,
        boundary_coverage=boundary_coverage,
        defaulted_responses=defaulted_responses,
        app_exception=app_exception,
    )


def _display_boundary_name(boundary: str) -> str:
    if boundary == "sqlalchemy":
        return "SQLAlchemy"
    return boundary.capitalize()


def _next_step_for_replay(
    seed: str,
    classification: ReplayClassification,
    fault_context: ReplayFaultContext,
) -> str:
    if classification is ReplayClassification.UNCHANGED:
        return "No action needed. This seed still matches the baseline."

    if fault_context.app_exception is not None:
        exception_type = fault_context.app_exception.removeprefix("Uncaught ").split(":", 1)[0]
        return f"Handle the uncaught {exception_type} and rerun `litmus replay {seed}`."

    if fault_context.defaulted_responses:
        return (
            f"Decide whether the defaulted outbound request needs an explicit simulator fixture, "
            f"then rerun `litmus replay {seed}`."
        )

    if fault_context.injected_faults:
        return f"Inspect the injected fault path and rerun `litmus replay {seed}`."

    if fault_context.boundary_coverage:
        return f"Inspect the cross-layer DST coverage for `litmus replay {seed}` and widen support or fix the path."

    return f"Review the changed response and rerun `litmus replay {seed}` after fixing it or updating the baseline."
