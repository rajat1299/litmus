from __future__ import annotations

from litmus.replay.differential import ReplayClassification
from litmus.replay.models import ReplayExplanation, ReplayFaultContext, ReplayResponseDetails
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
