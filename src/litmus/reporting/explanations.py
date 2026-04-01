from __future__ import annotations

from litmus.replay.models import ReplayExplanation


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
        "Why Litmus flagged this:",
    ]

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
    lines.extend(f"- {item}" for item in explanation.fault_context.defaulted_responses)
    if explanation.fault_context.app_exception is not None:
        lines.append(f"- {explanation.fault_context.app_exception}")
    return lines
