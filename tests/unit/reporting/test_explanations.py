from __future__ import annotations

from litmus.replay.differential import ReplayClassification
from litmus.replay.models import (
    ReplayCheckpoint,
    ReplayExplanation,
    ReplayFaultContext,
    ReplayFidelityResult,
    ReplayFidelityStatus,
    ReplayResponseDetails,
)
from litmus.reporting.explanations import render_replay_explanation


def test_render_replay_explanation_outputs_actionable_sections() -> None:
    explanation = ReplayExplanation(
        seed="seed:3",
        method="POST",
        path="/payments/charge",
        classification=ReplayClassification.BREAKING_CHANGE,
        baseline=ReplayResponseDetails(status_code=200, body={"status": "charged"}),
        current=ReplayResponseDetails(status_code=500, body={"status": "broken"}),
        reasons=[
            "Status code regressed from 200 to 500.",
            "Response body changed from {'status': 'charged'} to {'status': 'broken'}.",
        ],
        fault_context=ReplayFaultContext(
            selected_faults=["Step 1 scheduled timeout on http."],
            injected_faults=["Injected timeout on http for https://service.invalid/orders/123 at step 1."],
        ),
        fidelity=ReplayFidelityResult(
            status=ReplayFidelityStatus.MATCHED,
            reason="Replay execution matched the recorded transcript.",
        ),
        next_step="Inspect the timeout handling path and rerun `litmus replay seed:3`.",
        trace_kinds=["fault_plan_selected", "fault_injected", "request_completed"],
    )

    assert render_replay_explanation(explanation) == "\n".join(
        [
            "Litmus replay",
            "Seed: seed:3",
            "Route: POST /payments/charge",
            "Classification: breaking_change",
            "",
            "Expected:",
            "- Status: 200",
            "- Body: {'status': 'charged'}",
            "",
            "Observed:",
            "- Status: 500",
            "- Body: {'status': 'broken'}",
            "",
            "Execution fidelity: matched",
            "",
            "Why Litmus flagged this:",
            "- Status code regressed from 200 to 500.",
            "- Response body changed from {'status': 'charged'} to {'status': 'broken'}.",
            "",
            "Fault context:",
            "- Step 1 scheduled timeout on http.",
            "- Injected timeout on http for https://service.invalid/orders/123 at step 1.",
            "",
            "Next step:",
            "- Inspect the timeout handling path and rerun `litmus replay seed:3`.",
            "",
            "Trace:",
            "- fault_plan_selected",
            "- fault_injected",
            "- request_completed",
        ]
    )


def test_render_replay_explanation_surfaces_first_execution_divergence() -> None:
    explanation = ReplayExplanation(
        seed="seed:7",
        method="POST",
        path="/payments/charge",
        classification=ReplayClassification.UNCHANGED,
        baseline=ReplayResponseDetails(status_code=200, body={"status": "charged"}),
        current=ReplayResponseDetails(status_code=200, body={"status": "charged"}),
        reasons=["Current behavior still matches the baseline response."],
        fidelity=ReplayFidelityResult(
            status=ReplayFidelityStatus.DRIFTED,
            recorded_step=2,
            replay_step=2,
            reason="Replay execution diverged from the recorded transcript.",
            recorded_checkpoint=ReplayCheckpoint(kind="fault_injected", target="http", detail="timeout"),
            replay_checkpoint=ReplayCheckpoint(kind="response_completed", status_code=200),
        ),
        next_step="No action needed. This seed still matches the baseline.",
        trace_kinds=["fault_plan_selected", "request_completed"],
    )

    rendered = render_replay_explanation(explanation)

    assert "Execution fidelity: drifted" in rendered
    assert "- Recorded step 2: fault_injected on http (timeout)" in rendered
    assert "- Replay step 2: response_completed (status 200)" in rendered
