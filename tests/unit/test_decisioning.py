from __future__ import annotations

from litmus.decisioning import (
    MergeRecommendation,
    RiskLevel,
    VerificationDecision,
    evaluate_verification_result,
)
from litmus.discovery.routes import RouteDefinition
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
from litmus.scenarios.builder import Scenario


def test_evaluate_verification_result_marks_supported_clean_run_safe() -> None:
    confirmed_invariant = Invariant(
        name="charge_returns_200",
        source="mined:test_payments.py::test_charge_returns_200",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.PROPERTY,
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
        invariants=[confirmed_invariant],
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[
            RouteDefinition(
                method="POST",
                path="/payments/charge",
                handler_name="charge",
                file_path="service/app.py",
            )
        ],
        invariants=[confirmed_invariant],
        scenarios=[scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=200, json={"status": "charged"}),
                classification=ReplayClassification.UNCHANGED,
            )
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:1",
                seed_value=1,
                app_reference="service.app:app",
                method="POST",
                path="/payments/charge",
                request_payload={"amount": 100},
                baseline_status_code=200,
                baseline_body={"status": "charged"},
                trace=[
                    TraceEvent(kind="boundary_detected", metadata={"boundary": "http"}),
                    TraceEvent(
                        kind="boundary_intercepted",
                        metadata={"boundary": "http", "supported_shape": "httpx.AsyncClient"},
                    ),
                    TraceEvent(kind="boundary_simulated", metadata={"boundary": "http"}),
                ],
            )
        ],
        property_results=[
            PropertyCheckResult(
                invariant=confirmed_invariant,
                status=PropertyCheckStatus.PASSED,
            )
        ],
    )

    decision = evaluate_verification_result(result)

    assert decision.verdict.decision is VerificationDecision.SAFE
    assert decision.policy.merge_recommendation is MergeRecommendation.ALLOW
    assert decision.risk.level is RiskLevel.ELEVATED
    assert decision.risk.risk_classes == [
        "reliability",
        "correctness",
        "external_dependency",
    ]
    assert decision.risk.unsupported_gaps == []
    assert decision.policy.failing_checks == []


def test_evaluate_verification_result_marks_unsupported_boundary_for_deeper_verification() -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=200, json={"status": "charged"}),
                classification=ReplayClassification.UNCHANGED,
            )
        ],
        replay_traces=[
            ReplayTraceRecord(
                seed="seed:1",
                seed_value=1,
                app_reference="service.app:app",
                method="POST",
                path="/payments/charge",
                request_payload={"amount": 100},
                baseline_status_code=200,
                baseline_body={"status": "charged"},
                trace=[
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

    decision = evaluate_verification_result(result)

    assert decision.verdict.decision is VerificationDecision.NEEDS_DEEPER_VERIFICATION
    assert decision.policy.merge_recommendation is MergeRecommendation.REVIEW_REQUIRED
    assert decision.risk.level is RiskLevel.HIGH
    assert [gap.boundary for gap in decision.risk.unsupported_gaps] == ["redis"]
    assert decision.policy.failing_checks == ["supported_boundary_coverage"]


def test_evaluate_verification_result_marks_breaking_replay_unsafe() -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=500, json={"status": "broken"}),
                classification=ReplayClassification.BREAKING_CHANGE,
            )
        ],
        replay_traces=[],
        property_results=[],
    )

    decision = evaluate_verification_result(result)

    assert decision.verdict.decision is VerificationDecision.UNSAFE
    assert decision.policy.merge_recommendation is MergeRecommendation.BLOCK
    assert "blocking_regressions" in decision.policy.failing_checks


def test_evaluate_verification_result_marks_missing_signals_insufficient_evidence() -> None:
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[],
        replay_results=[],
        replay_traces=[],
        property_results=[],
    )

    decision = evaluate_verification_result(result)

    assert decision.verdict.decision is VerificationDecision.INSUFFICIENT_EVIDENCE
    assert decision.policy.merge_recommendation is MergeRecommendation.REVIEW_REQUIRED
    assert decision.policy.failing_checks == ["sufficient_evidence"]
    assert decision.evidence.total_signals == 0


def test_evaluate_verification_result_uses_strict_local_policy_to_block_missing_evidence() -> None:
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[],
        invariants=[],
        scenarios=[],
        replay_results=[],
        replay_traces=[],
        property_results=[],
        decision_policy="strict_local_v1",
    )

    decision = evaluate_verification_result(result)

    assert decision.verdict.decision is VerificationDecision.INSUFFICIENT_EVIDENCE
    assert decision.policy.policy_name == "strict_local_v1"
    assert decision.policy.merge_recommendation is MergeRecommendation.BLOCK
    assert decision.policy.failing_checks == ["sufficient_evidence"]
    assert decision.policy.checks[1].blocking is True


def test_evaluate_verification_result_marks_selected_route_gap_as_elevated_risk() -> None:
    suggested_invariant = Invariant(
        name="refund_needs_review",
        source="manual:suggested",
        status=InvariantStatus.SUGGESTED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/refund"),
        reasoning="Review refund behavior before trusting this endpoint.",
    )
    result = VerificationResult(
        app_reference="service.app:app",
        routes=[
            RouteDefinition(
                method="POST",
                path="/payments/refund",
                handler_name="refund",
                file_path="service/app.py",
            )
        ],
        invariants=[suggested_invariant],
        scenarios=[],
        replay_results=[],
        replay_traces=[],
        property_results=[],
    )

    decision = evaluate_verification_result(result)

    assert decision.verdict.decision is VerificationDecision.INSUFFICIENT_EVIDENCE
    assert decision.policy.merge_recommendation is MergeRecommendation.REVIEW_REQUIRED
    assert decision.risk.level is RiskLevel.ELEVATED
    assert decision.risk.risk_classes == ["reliability", "correctness"]
