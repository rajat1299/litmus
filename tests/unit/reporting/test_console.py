from __future__ import annotations

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
from litmus.reporting.console import render_verification_summary
from litmus.scenarios.builder import Scenario
from litmus.search_budget import ScenarioSearchBudget


def test_render_verification_summary_outputs_expected_copy_contract() -> None:
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
        reasoning="Review refund behavior before trusting this endpoint.",
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
                    TraceEvent(kind="fault_injected", metadata={"target": "http"}),
                    TraceEvent(kind="boundary_detected", metadata={"boundary": "redis"}),
                    TraceEvent(
                        kind="boundary_unsupported",
                        metadata={
                            "boundary": "redis",
                            "detail": "Unsupported constructor or type import in loaded app modules.",
                        },
                    ),
                ],
                search_budget=ScenarioSearchBudget(
                    requested_seeds=3,
                    allocated_seeds=1,
                    redistributed_seeds=-2,
                    allocation_mode="no_boundary",
                    priority_class="no_boundary",
                    frontier_capacity=1,
                    selected_targets=(),
                    planned_fault_kinds=(),
                    scenario_seed_start=1,
                    scenario_seed_end=1,
                ),
            )
        ],
        property_results=[
            PropertyCheckResult(invariant=confirmed_invariant, status=PropertyCheckStatus.PASSED),
            PropertyCheckResult(invariant=suggested_invariant, status=PropertyCheckStatus.SKIPPED),
        ],
    )

    assert render_verification_summary(result) == "\n".join(
        [
            "Litmus verify",
            "Surface: grounded alpha for Python async ASGI services",
            "App: service.app:app",
            "Scope: full repo",
            "Routes: 1",
            "Invariants: 2",
            "Confirmed invariants: 1",
            "Suggested invariants: 1",
            "Scenarios: 1",
            "Replay: unchanged=1 breaking=1 benign=0 improvement=0",
            "Properties: passed=1 failed=0 skipped=1",
            "Performance: elapsed=2.10s budget<=10.00s mode=local profile=default strategy=balanced within_budget=yes",
            "Launch budgets: replay_seeds/scenario=3 property_examples=100",
            "Search budget: requested_total=3 allocated_total=1 executed=1 single_target=0 kind_diverse=0 priority_multi=0 frontier_capped=1 redistributed=1 no_boundary=1 targets=none kinds=none",
            "Budget policy: launch-default under-10s path",
            "Confidence: 0.67",
            "DST coverage:",
            "- http: detected, intercepted, simulated, faulted",
            "- redis: unsupported, detected",
            "Compatibility:",
            "- http: supported",
            "- sqlalchemy: not detected",
            "- redis: unsupported (Unsupported constructor or type import in loaded app modules.)",
            "Pending invariant review:",
            "- refund_needs_review: Review refund behavior before trusting this endpoint.",
        ]
    )
