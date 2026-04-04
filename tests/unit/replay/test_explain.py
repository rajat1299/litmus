from __future__ import annotations

from litmus.dst.runtime import TraceEvent
from litmus.replay.differential import ReplayClassification
from litmus.replay.explain import explain_replay
from litmus.replay.models import ReplayCheckpoint, ReplayFidelityResult, ReplayFidelityStatus


def test_explain_replay_extracts_reasons_fault_context_and_next_step() -> None:
    explanation = explain_replay(
        seed="seed:1",
        method="GET",
        path="/health",
        baseline_status_code=200,
        baseline_body={"status": "ok"},
        current_status_code=500,
        current_body={"error": "uncaught_exception"},
        classification=ReplayClassification.BREAKING_CHANGE,
        diff={
            "status_code": (200, 500),
            "body": ({"status": "ok"}, {"error": "uncaught_exception"}),
        },
        trace=[
            TraceEvent(
                kind="fault_plan_selected",
                metadata={
                    "schedule": [
                        {"step": 1, "target": "http", "kind": "timeout", "params": {}},
                    ]
                },
            ),
            TraceEvent(
                kind="fault_injected",
                metadata={
                    "step": 1,
                    "target": "http",
                    "fault_kind": "timeout",
                    "url": "https://service.invalid/orders/123",
                    "params": {},
                },
            ),
            TraceEvent(
                kind="http_response_defaulted",
                metadata={
                    "step": 2,
                    "method": "GET",
                    "url": "https://service.invalid/orders/secondary",
                },
            ),
            TraceEvent(
                kind="app_exception",
                metadata={
                    "type": "ReadTimeout",
                    "message": "simulated timeout for GET https://service.invalid/orders/123",
                },
            ),
        ],
    )

    assert explanation.reasons == [
        "Status code regressed from 200 to 500.",
        "Response body changed from {'status': 'ok'} to {'error': 'uncaught_exception'}.",
    ]
    assert explanation.fault_context.selected_faults == [
        "Step 1 scheduled timeout on http.",
    ]
    assert explanation.fault_context.injected_faults == [
        "Injected timeout on http for https://service.invalid/orders/123 at step 1.",
    ]
    assert explanation.fault_context.defaulted_responses == [
        "Used Litmus default JSON response for GET https://service.invalid/orders/secondary at step 2.",
    ]
    assert explanation.fault_context.app_exception == (
        "Uncaught ReadTimeout: simulated timeout for GET https://service.invalid/orders/123"
    )
    assert explanation.next_step == (
        "Handle the uncaught ReadTimeout and rerun `litmus replay seed:1`."
    )
    assert explanation.trace_kinds == [
        "fault_plan_selected",
        "fault_injected",
        "http_response_defaulted",
        "app_exception",
    ]


def test_explain_replay_for_unchanged_seed_recommends_no_action() -> None:
    explanation = explain_replay(
        seed="seed:5",
        method="POST",
        path="/payments/charge",
        baseline_status_code=200,
        baseline_body={"status": "charged"},
        current_status_code=200,
        current_body={"status": "charged"},
        classification=ReplayClassification.UNCHANGED,
        diff={},
        trace=[TraceEvent(kind="request_started")],
    )

    assert explanation.reasons == ["Current behavior still matches the baseline response."]
    assert explanation.next_step == "No action needed. This seed still matches the baseline."


def test_explain_replay_attaches_execution_fidelity() -> None:
    explanation = explain_replay(
        seed="seed:7",
        method="POST",
        path="/payments/charge",
        baseline_status_code=200,
        baseline_body={"status": "charged"},
        current_status_code=200,
        current_body={"status": "charged"},
        classification=ReplayClassification.UNCHANGED,
        diff={},
        trace=[TraceEvent(kind="request_completed", metadata={"status_code": 200})],
        fidelity=ReplayFidelityResult(
            status=ReplayFidelityStatus.DRIFTED,
            recorded_step=2,
            replay_step=2,
            reason="Replay execution diverged from the recorded transcript.",
            recorded_checkpoint=ReplayCheckpoint(kind="fault_injected", target="http", detail="timeout"),
            replay_checkpoint=ReplayCheckpoint(kind="response_completed", status_code=200),
        ),
    )

    assert explanation.fidelity.status is ReplayFidelityStatus.DRIFTED
    assert explanation.fidelity.recorded_step == 2
    assert explanation.fidelity.replay_checkpoint == ReplayCheckpoint(kind="response_completed", status_code=200)
