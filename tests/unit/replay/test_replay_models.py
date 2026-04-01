from __future__ import annotations

from litmus.replay.differential import ReplayClassification
from litmus.replay.models import ReplayExplanation, ReplayFaultContext, ReplayResponseDetails


def test_replay_explanation_round_trips_through_dict_payload() -> None:
    explanation = ReplayExplanation(
        seed="seed:7",
        method="POST",
        path="/payments/charge",
        classification=ReplayClassification.BREAKING_CHANGE,
        baseline=ReplayResponseDetails(status_code=200, body={"status": "charged"}),
        current=ReplayResponseDetails(status_code=500, body={"status": "broken"}),
        reasons=["Status code regressed from 200 to 500."],
        fault_context=ReplayFaultContext(
            selected_faults=["Step 1 scheduled timeout on http."],
            injected_faults=["Injected timeout on http for https://service.invalid/orders/123."],
            defaulted_responses=["Used Litmus default JSON response for GET https://service.invalid/orders/secondary."],
            app_exception="Uncaught ReadTimeout: simulated timeout for GET https://service.invalid/orders/123",
        ),
        next_step="Handle the uncaught ReadTimeout and rerun `litmus replay seed:7`.",
        trace_kinds=["fault_plan_selected", "request_started", "fault_injected", "app_exception"],
    )

    payload = explanation.to_dict()
    restored = ReplayExplanation.from_dict(payload)

    assert restored == explanation
