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

    assert "## Litmus Verification (Grounded Alpha)" in comment
    assert "Surface: `Python async ASGI services`" in comment
    assert "### Decision" in comment
    assert "- Verdict: `unsafe`" in comment
    assert "- Merge recommendation: `block`" in comment
    assert "- Risk: `high` (`reliability`, `correctness`)" in comment
    assert "- Failed policy checks: `blocking_regressions`" in comment
    assert "Confidence score: `0.33`" in comment
    assert "- `POST /payments/charge`" in comment
    assert "- `GET /health`" in comment
    assert "- Invariants: total=1 confirmed=1 suggested=0" in comment
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

    assert "## Litmus Verification (Grounded Alpha)" in comment
    assert "Surface: `Python async ASGI services`" in comment
    assert "- Verdict: `safe`" in comment
    assert "- Merge recommendation: `allow`" in comment
    assert "Confidence score: `1.00`" in comment
    assert "- Invariants: total=0 confirmed=0 suggested=0" in comment
    assert "### Failing Seeds" in comment
    assert "- No failing seeds recorded." in comment
    assert "### What Went Wrong" in comment
    assert "- No breaking replay or property failures detected." in comment


def test_render_pr_comment_includes_compatibility_section_for_supported_and_unsupported_boundaries() -> None:
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
                trace=[
                    TraceEvent(kind="boundary_detected", metadata={"boundary": "http"}),
                    TraceEvent(
                        kind="boundary_intercepted",
                        metadata={"boundary": "http", "supported_shape": "httpx.AsyncClient"},
                    ),
                    TraceEvent(kind="boundary_simulated", metadata={"boundary": "http"}),
                    TraceEvent(kind="boundary_detected", metadata={"boundary": "redis"}),
                    TraceEvent(
                        kind="boundary_unsupported",
                        metadata={
                            "boundary": "redis",
                            "detail": "Unsupported constructor or type import in loaded app modules.",
                        },
                    ),
                ],
            )
        ],
        property_results=[],
    )

    comment = render_pr_comment(result)

    assert "### Compatibility" in comment
    assert "- `http`: supported" in comment
    assert "- `sqlalchemy`: not detected" in comment
    assert (
        "- `redis`: unsupported (`Unsupported constructor or type import in loaded app modules.`)"
        in comment
    )


def test_render_pr_comment_surfaces_suggested_invariants_needing_review() -> None:
    suggested_invariant = Invariant(
        name="refund_post_payments_refund_needs_confirmed_anchor",
        source="suggested:route_gap",
        status=InvariantStatus.SUGGESTED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/refund"),
        reasoning=(
            "POST /payments/refund is selected for verification without a confirmed mined invariant "
            "anchor. Add or approve a baseline before trusting verification coverage."
        ),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[suggested_invariant],
        scenarios=[],
        replay_results=[],
        replay_traces=[],
        property_results=[],
    )

    comment = render_pr_comment(result)

    assert "- `POST /payments/refund`" in comment
    assert "### Pending Invariant Review" in comment
    assert (
        "- Pending review for suggested invariant `refund_post_payments_refund_needs_confirmed_anchor` on "
        "`POST /payments/refund`: POST /payments/refund is selected for verification without a "
        "confirmed mined invariant anchor. Add or approve a baseline before trusting verification "
        "coverage."
    ) in comment
    assert "- No breaking replay or property failures detected." not in comment


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
