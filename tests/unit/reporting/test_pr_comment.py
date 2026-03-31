from __future__ import annotations

from litmus.dst.engine import VerificationResult
from litmus.dst.runtime import TraceEvent
from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)
from litmus.properties.runner import PropertyCheckResult, PropertyCheckStatus
from litmus.replay.differential import DifferentialReplayResult, ReplayClassification
from litmus.replay.trace import ReplayTraceRecord
from litmus.reporting.pr_comment import render_pr_comment
from litmus.scenarios.builder import Scenario


def test_render_pr_comment_summarizes_failures_with_replay_commands() -> None:
    charge_scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    health_scenario = Scenario(
        method="GET",
        path="/health",
        request=RequestExample(method="GET", path="/health"),
        expected_response=ResponseExample(status_code=200, json={"status": "ok"}),
    )
    failed_property_invariant = Invariant(
        name="charge_never_500s",
        source="mined:test_payments.py::test_charge_returns_200_on_success",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.PROPERTY,
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[failed_property_invariant],
        scenarios=[charge_scenario, health_scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=charge_scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=500, json={"status": "broken"}),
                classification=ReplayClassification.BREAKING_CHANGE,
                diff={
                    "status_code": (200, 500),
                    "body": ({"status": "charged"}, {"status": "broken"}),
                },
            ),
            DifferentialReplayResult(
                scenario=health_scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "ok"}),
                changed_response=ResponseExample(status_code=200, json={"status": "ok"}),
                classification=ReplayClassification.UNCHANGED,
            ),
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:7",
                seed_value=7,
                app_reference="service.app:app",
                method="POST",
                path="/payments/charge",
                request_payload={"amount": 100},
                baseline_status_code=200,
                baseline_body={"status": "charged"},
                trace=[TraceEvent(kind="request_started")],
            ),
            ReplayTraceRecord(
                seed="seed:8",
                seed_value=8,
                app_reference="service.app:app",
                method="GET",
                path="/health",
                request_payload=None,
                baseline_status_code=200,
                baseline_body={"status": "ok"},
                trace=[TraceEvent(kind="request_started")],
            ),
        ],
        property_results=[
            PropertyCheckResult(
                invariant=failed_property_invariant,
                status=PropertyCheckStatus.FAILED,
                failing_request=RequestExample(
                    method="POST",
                    path="/payments/charge",
                    json={"amount": 1000},
                ),
            )
        ],
    )

    comment = render_pr_comment(result)

    assert "## Litmus Verification" in comment
    assert "Confidence score: `0.33`" in comment
    assert "- `POST /payments/charge`" in comment
    assert "- `GET /health`" in comment
    assert "- Replay: unchanged=1 breaking=1 benign=0 improvement=0" in comment
    assert "- Properties: passed=0 failed=1 skipped=0" in comment
    assert "- `seed:7` on `POST /payments/charge` -> `litmus replay seed:7`" in comment
    assert (
        "- Replay regression on `POST /payments/charge`: status `200` -> `500`, "
        'body `{"status": "charged"}` -> `{"status": "broken"}`.'
    ) in comment
    assert (
        '- Property invariant `charge_never_500s` failed for `POST /payments/charge` with request '
        '`{"amount": 1000}`.'
    ) in comment


def test_render_pr_comment_reports_clean_verification_runs() -> None:
    health_scenario = Scenario(
        method="GET",
        path="/health",
        request=RequestExample(method="GET", path="/health"),
        expected_response=ResponseExample(status_code=200, json={"status": "ok"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[health_scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=health_scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "ok"}),
                changed_response=ResponseExample(status_code=200, json={"status": "ok"}),
                classification=ReplayClassification.UNCHANGED,
            )
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:1",
                seed_value=1,
                app_reference="service.app:app",
                method="GET",
                path="/health",
                request_payload=None,
                baseline_status_code=200,
                baseline_body={"status": "ok"},
                trace=[TraceEvent(kind="request_started")],
            )
        ],
        property_results=[],
    )

    comment = render_pr_comment(result)

    assert "Confidence score: `1.00`" in comment
    assert "### Failing Seeds" in comment
    assert "- No failing seeds recorded." in comment
    assert "### What Went Wrong" in comment
    assert "- No breaking replay or property failures detected." in comment


def test_render_pr_comment_reports_missing_replay_trace_for_breaking_result() -> None:
    charge_scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[charge_scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=charge_scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=500, json={"status": "broken"}),
                classification=ReplayClassification.BREAKING_CHANGE,
                diff={
                    "status_code": (200, 500),
                    "body": ({"status": "charged"}, {"status": "broken"}),
                },
            )
        ],
        replay_traces=[],
        property_results=[],
    )

    comment = render_pr_comment(result)

    assert "- No failing seeds recorded." not in comment
    assert (
        "- Replay trace missing for `POST /payments/charge`; rerun `litmus verify` before replaying."
    ) in comment


def test_render_pr_comment_matches_replay_seed_by_scenario_identity_not_trace_order() -> None:
    charge_scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    refund_scenario = Scenario(
        method="POST",
        path="/payments/refund",
        request=RequestExample(method="POST", path="/payments/refund", json={"amount": 50}),
        expected_response=ResponseExample(status_code=200, json={"status": "refunded"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[charge_scenario, refund_scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=charge_scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=500, json={"status": "broken"}),
                classification=ReplayClassification.BREAKING_CHANGE,
                diff={"status_code": (200, 500)},
            ),
            DifferentialReplayResult(
                scenario=refund_scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "refunded"}),
                changed_response=ResponseExample(status_code=500, json={"status": "failed"}),
                classification=ReplayClassification.BREAKING_CHANGE,
                diff={"status_code": (200, 500)},
            ),
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:2",
                seed_value=2,
                app_reference="service.app:app",
                method="POST",
                path="/payments/refund",
                request_payload={"amount": 50},
                baseline_status_code=200,
                baseline_body={"status": "refunded"},
                trace=[TraceEvent(kind="request_started")],
            ),
            ReplayTraceRecord(
                seed="seed:1",
                seed_value=1,
                app_reference="service.app:app",
                method="POST",
                path="/payments/charge",
                request_payload={"amount": 100},
                baseline_status_code=200,
                baseline_body={"status": "charged"},
                trace=[TraceEvent(kind="request_started")],
            ),
        ],
        property_results=[],
    )

    comment = render_pr_comment(result)

    assert "- `seed:1` on `POST /payments/charge` -> `litmus replay seed:1`" in comment
    assert "- `seed:2` on `POST /payments/refund` -> `litmus replay seed:2`" in comment


def test_render_pr_comment_preserves_distinct_seeds_for_same_scenario() -> None:
    charge_scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[charge_scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=charge_scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=500, json={"status": "broken"}),
                classification=ReplayClassification.BREAKING_CHANGE,
                diff={"status_code": (200, 500)},
            ),
            DifferentialReplayResult(
                scenario=charge_scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=500, json={"status": "still broken"}),
                classification=ReplayClassification.BREAKING_CHANGE,
                diff={"status_code": (200, 500)},
            ),
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:7",
                seed_value=7,
                app_reference="service.app:app",
                method="POST",
                path="/payments/charge",
                request_payload={"amount": 100},
                baseline_status_code=200,
                baseline_body={"status": "charged"},
                trace=[TraceEvent(kind="request_started")],
            ),
            ReplayTraceRecord(
                seed="seed:9",
                seed_value=9,
                app_reference="service.app:app",
                method="POST",
                path="/payments/charge",
                request_payload={"amount": 100},
                baseline_status_code=200,
                baseline_body={"status": "charged"},
                trace=[TraceEvent(kind="request_started")],
            ),
        ],
        property_results=[],
    )

    comment = render_pr_comment(result)

    assert comment.count("`seed:7` on `POST /payments/charge` -> `litmus replay seed:7`") == 1
    assert comment.count("`seed:9` on `POST /payments/charge` -> `litmus replay seed:9`") == 1
