from __future__ import annotations

import pytest

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
        started_at="2026-04-07T12:00:00+00:00",
        completed_at="2026-04-07T12:00:02.100000+00:00",
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
                        metadata={"boundary": "http", "supported_shape": "httpx/aiohttp"},
                    ),
                    TraceEvent(kind="boundary_simulated", metadata={"boundary": "http"}),
                    TraceEvent(
                        kind="boundary_detected",
                        metadata={"boundary": "redis"},
                    ),
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
    assert projection.performance == {
        "mode": "local",
        "fault_profile": "default",
        "budget_policy": "launch_default",
        "measured": True,
        "elapsed_ms": 2100,
        "budget_ms": 10000,
        "within_budget": True,
        "replay_seeds_per_scenario": 3,
        "property_max_examples": 100,
    }
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
    assert projection.compatibility["matrix"]["python"] == "3.11+"
    assert projection.compatibility["matrix"]["http"]["package"] == "httpx/aiohttp"
    assert projection.compatibility["boundaries"]["http"] == {
        "status": "supported",
        "detected": True,
        "intercepted": True,
        "simulated": True,
        "faulted": False,
        "unsupported": False,
        "supported_shapes": ["httpx/aiohttp"],
        "unsupported_details": [],
    }
    assert projection.compatibility["boundaries"]["sqlalchemy"]["status"] == "not_detected"
    assert projection.compatibility["boundaries"]["redis"] == {
        "status": "unsupported",
        "detected": True,
        "intercepted": False,
        "simulated": False,
        "faulted": False,
        "unsupported": True,
        "supported_shapes": [],
        "unsupported_details": [
            "Unsupported constructor or type import in loaded app modules."
        ],
    }
    assert projection.confidence == pytest.approx(2 / 3, rel=1e-6)
    assert summarize_verification_result(result) == projection.to_dict()


def test_verification_projection_marks_mixed_boundary_usage_as_partial() -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    result = VerificationResult(
        app_reference="service.app:app",
        started_at="2026-04-07T12:00:00+00:00",
        completed_at="2026-04-07T12:00:12+00:00",
        mode="ci",
        scope_label="full repo",
        routes=[],
        invariants=[],
        scenarios=[scenario],
        replay_results=[],
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
                        kind="boundary_intercepted",
                        metadata={"boundary": "redis", "supported_shape": "redis.asyncio.Redis.from_url"},
                    ),
                    TraceEvent(kind="boundary_simulated", metadata={"boundary": "redis"}),
                ],
            ),
            ReplayTraceRecord(
                seed="seed:2",
                seed_value=2,
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
            ),
        ],
        property_results=[],
    )

    projection = VerificationProjection.from_result(result)

    assert projection.performance == {
        "mode": "ci",
        "fault_profile": "default",
        "budget_policy": "ci_deeper",
        "measured": True,
        "elapsed_ms": 12000,
        "budget_ms": 60000,
        "within_budget": True,
        "replay_seeds_per_scenario": 500,
        "property_max_examples": 500,
    }
    assert projection.compatibility["boundaries"]["redis"]["status"] == "partial"
    assert projection.compatibility["boundaries"]["redis"]["supported_shapes"] == [
        "redis.asyncio.Redis.from_url"
    ]
    assert projection.compatibility["boundaries"]["redis"]["unsupported_details"] == [
        "Unsupported constructor or type import in loaded app modules."
    ]


def test_verification_projection_marks_hostile_local_profile_as_opt_in_deeper_path() -> None:
    result = VerificationResult(
        app_reference="service.app:app",
        started_at="2026-04-07T12:00:00+00:00",
        completed_at="2026-04-07T12:00:04+00:00",
        mode="local",
        fault_profile="hostile",
        scope_label="full repo",
        routes=[],
        invariants=[],
        scenarios=[],
        replay_results=[],
        replay_traces=[],
        property_results=[],
    )

    projection = VerificationProjection.from_result(result)

    assert projection.performance == {
        "mode": "local",
        "fault_profile": "hostile",
        "budget_policy": "local_deeper_opt_in",
        "measured": True,
        "elapsed_ms": 4000,
        "budget_ms": 10000,
        "within_budget": True,
        "replay_seeds_per_scenario": 9,
        "property_max_examples": 250,
    }
