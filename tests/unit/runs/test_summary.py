from __future__ import annotations

import pytest

from litmus.discovery.routes import RouteDefinition
from litmus.dst.engine import VerificationResult
from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)
from litmus.properties.runner import PropertyCheckResult, PropertyCheckStatus
from litmus.replay.differential import DifferentialReplayResult, ReplayClassification
from litmus.runs.summary import VerificationProjection, summarize_verification_result
from litmus.scenarios.builder import Scenario


def test_verification_projection_owns_shared_verification_counts() -> None:
    confirmed_invariant = Invariant(
        name="charge_returns_200",
        source="mined:test_payments.py::test_charge_returns_200",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    suggested_invariant = Invariant(
        name="refund_needs_review",
        source="suggested:route_gap",
        status=InvariantStatus.SUGGESTED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/refund"),
        reasoning="Review refund behavior.",
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
        scope_label="full repo",
        routes=[
            RouteDefinition(
                method="POST",
                path="/payments/charge",
                handler_name="charge",
                file_path="service/app.py",
            )
        ],
        invariants=[confirmed_invariant, suggested_invariant],
        scenarios=[scenario],
        replay_results=[
            DifferentialReplayResult(
                scenario=scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=200, json={"status": "charged"}),
                classification=ReplayClassification.UNCHANGED,
            ),
            DifferentialReplayResult(
                scenario=scenario,
                baseline_response=ResponseExample(status_code=200, json={"status": "charged"}),
                changed_response=ResponseExample(status_code=500, json={"status": "broken"}),
                classification=ReplayClassification.BREAKING_CHANGE,
                diff={"status_code": (200, 500)},
            ),
        ],
        replay_traces=[],
        property_results=[
            PropertyCheckResult(invariant=confirmed_invariant, status=PropertyCheckStatus.PASSED),
            PropertyCheckResult(invariant=suggested_invariant, status=PropertyCheckStatus.SKIPPED),
        ],
    )

    projection = VerificationProjection.from_result(result)

    assert projection.app_reference == "service.app:app"
    assert projection.scope_label == "full repo"
    assert projection.routes == 1
    assert projection.scenarios == 1
    assert projection.invariants == {
        "total": 2,
        "confirmed": 1,
        "suggested": 1,
    }
    assert projection.replay == {
        "unchanged": 1,
        "breaking_change": 1,
        "benign_change": 0,
        "improvement": 0,
    }
    assert projection.properties == {
        "passed": 1,
        "failed": 0,
        "skipped": 1,
    }
    assert projection.confidence == pytest.approx(2 / 3, rel=1e-6)
    assert summarize_verification_result(result) == projection.to_dict()
