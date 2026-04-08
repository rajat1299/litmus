from __future__ import annotations

from litmus.replay.models import (
    ReplayCheckpoint,
    ReplayDriftKind,
    ReplayExplanation,
    ReplayFidelityResult,
    ReplayFidelityStatus,
    SchedulerDecision,
)


def render_replay_explanation(explanation: ReplayExplanation) -> str:
    lines = [
        "Litmus replay",
        f"Seed: {explanation.seed}",
        f"Route: {explanation.method} {explanation.path}",
        f"Classification: {explanation.classification.value}",
        "",
        "Expected:",
        f"- Status: {explanation.baseline.status_code}",
        f"- Body: {explanation.baseline.body}",
        "",
        "Observed:",
        f"- Status: {explanation.current.status_code}",
        f"- Body: {explanation.current.body}",
        "",
        f"Execution fidelity: {explanation.fidelity.status.value}",
        "",
        "Why Litmus flagged this:",
    ]

    lines.extend(_fidelity_context_lines(explanation.fidelity))
    lines.extend(f"- {reason}" for reason in explanation.reasons)

    fault_lines = _fault_context_lines(explanation)
    if fault_lines:
        lines.extend(
            [
                "",
                "Fault context:",
                *fault_lines,
            ]
        )

    lines.extend(
        [
            "",
            "Next step:",
            f"- {explanation.next_step}",
            "",
            "Trace:",
        ]
    )
    lines.extend(f"- {kind}" for kind in explanation.trace_kinds)
    return "\n".join(lines)


def _fault_context_lines(explanation: ReplayExplanation) -> list[str]:
    lines: list[str] = []
    lines.extend(f"- {item}" for item in explanation.fault_context.selected_faults)
    lines.extend(f"- {item}" for item in explanation.fault_context.injected_faults)
    lines.extend(f"- {item}" for item in explanation.fault_context.boundary_coverage)
    lines.extend(f"- {item}" for item in explanation.fault_context.defaulted_responses)
    if explanation.fault_context.app_exception is not None:
        lines.append(f"- {explanation.fault_context.app_exception}")
    return lines


def _fidelity_context_lines(fidelity: ReplayFidelityResult) -> list[str]:
    if fidelity.status is ReplayFidelityStatus.MATCHED:
        return []

    lines = [f"- {fidelity.reason}"]
    if fidelity.status is not ReplayFidelityStatus.DRIFTED:
        return lines

    if fidelity.drift_kind is not None:
        lines.append(f"- Scheduler drift kind: {fidelity.drift_kind.value}")

    if fidelity.drift_kind in {
        ReplayDriftKind.DECISION_MISMATCH,
        ReplayDriftKind.DECISION_MISSING,
        ReplayDriftKind.UNEXPECTED_DECISION,
    }:
        if fidelity.recorded_step is not None:
            lines.append(
                f"- Recorded decision {fidelity.recorded_step}: {_format_decision(fidelity.recorded_decision)}"
            )
        if fidelity.replay_step is not None:
            lines.append(
                f"- Replay decision {fidelity.replay_step}: {_format_decision(fidelity.replay_decision)}"
            )
        return lines

    if fidelity.recorded_step is not None:
        lines.append(
            f"- Recorded step {fidelity.recorded_step}: {_format_checkpoint(fidelity.recorded_checkpoint)}"
        )
    if fidelity.replay_step is not None:
        lines.append(
            f"- Replay step {fidelity.replay_step}: {_format_checkpoint(fidelity.replay_checkpoint)}"
        )
    return lines


def _format_checkpoint(checkpoint: ReplayCheckpoint | None) -> str:
    if checkpoint is None:
        return "missing"

    parts = [checkpoint.kind]
    if checkpoint.target is not None:
        parts.append(f"on {checkpoint.target}")
    if checkpoint.detail is not None:
        parts.append(f"({checkpoint.detail})")
    if checkpoint.status_code is not None:
        parts.append(f"(status {checkpoint.status_code})")
    return " ".join(parts)


def _format_decision(decision: SchedulerDecision | None) -> str:
    if decision is None:
        return "missing"

    parts = [decision.kind]
    if decision.target is not None:
        parts.append(f"on {decision.target}")
    if decision.detail is not None:
        parts.append(f"({decision.detail})")
    if decision.step is not None:
        parts.append(f"at step {decision.step}")
    return " ".join(parts)
