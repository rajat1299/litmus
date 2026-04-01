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

    rendered = render_replay_explanation(explanation)

    assert "Litmus replay" in rendered
    assert "Seed: seed:3" in rendered
    assert "Route: POST /payments/charge" in rendered
    assert "Classification: breaking_change" in rendered
    assert "Expected:" in rendered
    assert "Observed:" in rendered
    assert "Why Litmus flagged this:" in rendered
    assert "Fault context:" in rendered
    assert "Next step:" in rendered
    assert "Trace:" in rendered
    assert "- Status: 200" in rendered
    assert "- Injected timeout on http for https://service.invalid/orders/123 at step 1." in rendered
