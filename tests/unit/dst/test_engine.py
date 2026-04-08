from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
import sys

from litmus.config import RepoConfig
from litmus.dst.engine import (
    _boundary_usage_for_loaded_app,
    _fault_targets_for_boundary_coverage,
    _fault_targets_for_loaded_app,
    _run_replay,
    _scenario_fault_targets,
    run_verification,
)
from litmus.dst.runtime import BoundaryCoverage, TraceEvent
from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import (
    Invariant,
    InvariantReview,
    InvariantReviewState,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)
from litmus.properties.runner import PropertyCheckStatus
from litmus.runs import RunMode
from litmus.scenarios.builder import Scenario


class _PaymentsApp:
    async def __call__(self, scope, receive, send) -> None:
        request = await receive()
        payload = json.loads(request["body"].decode("utf-8")) if request["body"] else {}
        amount = int(payload.get("amount", 0))
        if amount > 500:
            status_code = 402
            body = {"status": "declined"}
        else:
            status_code = 200
            body = {"status": "charged"}

        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps(body).encode("utf-8"),
            }
        )


def test_run_verification_uses_ci_replay_and_property_budgets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    captured: dict[str, int] = {}

    async def fake_run_replay(
        _app,
        _app_reference,
        _scenarios,
        *,
        seeds_per_scenario: int,
        search_strategy: str,
        fault_targets=None,
        boundary_usage=None,
        root=None,
    ):
        captured["seeds_per_scenario"] = seeds_per_scenario
        captured["search_strategy"] = search_strategy
        captured["fault_targets"] = fault_targets
        captured["boundary_usage"] = boundary_usage
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path, mode="ci")

    assert captured["seeds_per_scenario"] == 500
    assert captured["max_examples"] == 500
    assert captured["fault_targets"] == ["http"]
    assert captured["boundary_usage"].supported_targets == ()
    assert captured["boundary_usage"].unsupported_targets == ()


def test_run_verification_defaults_to_local_replay_and_property_budgets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    captured: dict[str, int] = {}

    async def fake_run_replay(
        _app,
        _app_reference,
        _scenarios,
        *,
        seeds_per_scenario: int,
        search_strategy: str,
        fault_targets=None,
        boundary_usage=None,
        root=None,
    ):
        captured["seeds_per_scenario"] = seeds_per_scenario
        captured["search_strategy"] = search_strategy
        captured["fault_targets"] = fault_targets
        captured["boundary_usage"] = boundary_usage
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path)

    assert captured["seeds_per_scenario"] == 3
    assert captured["search_strategy"] == "balanced"
    assert captured["max_examples"] == 100
    assert captured["fault_targets"] == ["http"]
    assert captured["boundary_usage"].supported_targets == ()
    assert captured["boundary_usage"].unsupported_targets == ()


def test_run_verification_uses_gentle_fault_profile_local_budgets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.load_repo_config", lambda _root: RepoConfig(fault_profile="gentle"))
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    captured: dict[str, int] = {}

    async def fake_run_replay(
        _app,
        _app_reference,
        _scenarios,
        *,
        seeds_per_scenario: int,
        search_strategy: str,
        fault_targets=None,
        boundary_usage=None,
        root=None,
    ):
        captured["seeds_per_scenario"] = seeds_per_scenario
        captured["search_strategy"] = search_strategy
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path)

    assert captured["seeds_per_scenario"] == 1
    assert captured["search_strategy"] == "balanced"
    assert captured["max_examples"] == 25


def test_run_verification_uses_hostile_fault_profile_local_budgets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.load_repo_config", lambda _root: RepoConfig(fault_profile="hostile"))
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    captured: dict[str, int] = {}

    async def fake_run_replay(
        _app,
        _app_reference,
        _scenarios,
        *,
        seeds_per_scenario: int,
        search_strategy: str,
        fault_targets=None,
        boundary_usage=None,
        root=None,
    ):
        captured["seeds_per_scenario"] = seeds_per_scenario
        captured["search_strategy"] = search_strategy
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path)

    assert captured["seeds_per_scenario"] == 9
    assert captured["search_strategy"] == "frontier_first"
    assert captured["max_examples"] == 250


def test_run_verification_keeps_watch_mode_balanced_under_hostile_profile(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.load_repo_config", lambda _root: RepoConfig(fault_profile="hostile"))
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    captured: dict[str, int | str] = {}

    async def fake_run_replay(
        _app,
        _app_reference,
        _scenarios,
        *,
        seeds_per_scenario: int,
        search_strategy: str,
        fault_targets=None,
        boundary_usage=None,
        root=None,
    ):
        captured["seeds_per_scenario"] = seeds_per_scenario
        captured["search_strategy"] = search_strategy
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path, mode=RunMode.WATCH)

    assert captured["seeds_per_scenario"] == 9
    assert captured["search_strategy"] == "balanced"
    assert captured["max_examples"] == 250


def test_run_replay_generates_requested_seed_count_per_scenario_and_fault_plans(monkeypatch) -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )

    @dataclass(slots=True)
    class FakeAsgiResult:
        status_code: int
        body: dict[str, str]
        trace: list[TraceEvent]
        boundary_coverage: dict[str, BoundaryCoverage]

    captured_fault_plan_seeds: list[int] = []
    captured_planned_faults: list[tuple[int, list[str], list[str] | None]] = []

    class FakeFaultPlan:
        def __init__(self, seed: int) -> None:
            self.seed = seed
            self.schedule = {1: {"kind": "timeout"}}

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str], kinds: list[str] | None = None):
        assert steps == 1
        captured_planned_faults.append((seed, list(targets), None if kinds is None else list(kinds)))
        return FakeFaultPlan(seed)

    async def fake_run_asgi_app(_app, *, method, path, json_body, seed, fault_plan=None):
        assert method == "POST"
        assert path == "/payments/charge"
        assert json_body == {"amount": 100}
        if fault_plan is not None and seed != 0:
            captured_fault_plan_seeds.append(fault_plan.seed)
        return FakeAsgiResult(
            status_code=200,
            body={"status": "charged"},
            trace=[TraceEvent(kind="request_started", metadata={"seed": seed})],
            boundary_coverage={
                "http": BoundaryCoverage(detected=True),
                "sqlalchemy": BoundaryCoverage(detected=True),
                "redis": BoundaryCoverage(detected=True),
            },
        )

    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    replay_results, replay_traces = asyncio.run(
        _run_replay(
            object(),
            "service.app:app",
            [scenario],
            seeds_per_scenario=3,
        )
    )

    assert len(replay_results) == 3
    assert len(replay_traces) == 3
    assert [trace.seed for trace in replay_traces] == ["seed:1", "seed:2", "seed:3"]
    assert captured_fault_plan_seeds == [1, 2, 3]
    assert [call for call in captured_planned_faults if call[0] > 0] == [
        (1, ["http"], ["timeout"]),
        (2, ["sqlalchemy"], ["connection_dropped"]),
        (3, ["redis"], ["timeout"]),
    ]


def test_run_replay_spreads_local_fault_targets_across_http_sqlalchemy_and_redis(monkeypatch) -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )

    captured_targets: list[str] = []

    class FakeFaultPlan:
        def __init__(self, seed: int, target: str) -> None:
            self.seed = seed
            self.schedule = {
                1: {
                    "kind": "fault",
                    "target": target,
                }
            }

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str], kinds: list[str] | None = None):
        assert steps == 1
        target = targets[0]
        if seed > 0:
            captured_targets.append(target)
        return FakeFaultPlan(seed, target)

    async def fake_run_asgi_app(_app, *, method, path, json_body, seed, fault_plan=None):
        assert method == "POST"
        assert path == "/payments/charge"
        assert json_body == {"amount": 100}
        return type(
            "FakeAsgiResult",
            (),
            {
                "status_code": 200,
                "body": {"status": "charged"},
                "trace": [TraceEvent(kind="request_started", metadata={"seed": seed})],
                "boundary_coverage": {
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(detected=True),
                    "redis": BoundaryCoverage(detected=True),
                },
            },
        )()

    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    replay_results, replay_traces = asyncio.run(
        _run_replay(
            object(),
            "service.app:app",
            [scenario],
            seeds_per_scenario=3,
        )
    )

    assert len(replay_results) == 3
    assert len(replay_traces) == 3
    assert captured_targets == ["http", "sqlalchemy", "redis"]
    assert replay_traces[0].search_budget is not None
    assert replay_traces[0].search_budget.to_dict() == {
        "requested_seeds": 3,
        "allocated_seeds": 3,
        "redistributed_seeds": 0,
        "allocation_mode": "target_spread",
        "priority_class": "multi_target",
        "frontier_capacity": 9,
        "selected_targets": ["http", "sqlalchemy", "redis"],
        "planned_fault_kinds": ["timeout", "connection_dropped"],
        "scenario_seed_start": 1,
        "scenario_seed_end": 3,
    }


def test_run_replay_diversifies_single_target_fault_kinds_before_repeating(monkeypatch) -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )

    captured_faults: list[tuple[str, str]] = []

    class FakeFaultPlan:
        def __init__(self, seed: int, target: str, kind: str) -> None:
            self.seed = seed
            self.schedule = {
                1: {
                    "kind": kind,
                    "target": target,
                }
            }

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str], kinds: list[str] | None = None):
        assert steps == 1
        target = targets[0]
        kind = "timeout" if kinds is None else kinds[0]
        if seed > 0:
            captured_faults.append((target, kind))
        return FakeFaultPlan(seed, target, kind)

    async def fake_run_asgi_app(_app, *, method, path, json_body, seed, fault_plan=None):
        assert method == "POST"
        assert path == "/payments/charge"
        assert json_body == {"amount": 100}
        return type(
            "FakeAsgiResult",
            (),
            {
                "status_code": 200,
                "body": {"status": "charged"},
                "trace": [TraceEvent(kind="request_started", metadata={"seed": seed})],
                "boundary_coverage": {
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(),
                    "redis": BoundaryCoverage(),
                },
            },
        )()

    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    replay_results, replay_traces = asyncio.run(
        _run_replay(
            object(),
            "service.app:app",
            [scenario],
            seeds_per_scenario=3,
        )
    )

    assert len(replay_results) == 3
    assert len(replay_traces) == 3
    assert captured_faults == [
        ("http", "timeout"),
        ("http", "connection_refused"),
        ("http", "http_error"),
    ]
    assert replay_traces[0].search_budget is not None
    assert replay_traces[0].search_budget.planned_fault_kinds == (
        "timeout",
        "connection_refused",
        "http_error",
    )


def test_run_replay_redistributes_saved_budget_from_no_boundary_to_complex_scenario(monkeypatch) -> None:
    health_scenario = Scenario(
        method="GET",
        path="/health",
        request=RequestExample(method="GET", path="/health"),
        expected_response=ResponseExample(status_code=200, json={"status": "ok"}),
    )
    charge_scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )

    observed_fault_runs: list[tuple[str, int, str, str]] = []

    class FakeFaultPlan:
        def __init__(self, seed: int, schedule: dict[int, dict[str, str]]) -> None:
            self.seed = seed
            self.schedule = schedule

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str] | None = None, kinds: list[str] | None = None):
        if steps == 0:
            return FakeFaultPlan(seed, {})
        assert targets is not None
        target = targets[0]
        kind = "timeout" if kinds is None else kinds[0]
        return FakeFaultPlan(seed, {1: {"target": target, "kind": kind}})

    async def fake_run_asgi_app(_app, *, method, path, json_body, seed, fault_plan=None):
        if path == "/health":
            return type(
                "FakeAsgiResult",
                (),
                {
                    "status_code": 200,
                    "body": {"status": "ok"},
                    "trace": [TraceEvent(kind="request_started", metadata={"seed": seed})],
                    "boundary_coverage": {
                        "http": BoundaryCoverage(),
                        "sqlalchemy": BoundaryCoverage(),
                        "redis": BoundaryCoverage(),
                    },
                },
            )()

        if fault_plan is not None and fault_plan.schedule:
            scheduled = fault_plan.schedule[1]
            observed_fault_runs.append((path, seed, scheduled["target"], scheduled["kind"]))
        return type(
            "FakeAsgiResult",
            (),
            {
                "status_code": 200,
                "body": {"status": "charged"},
                "trace": [TraceEvent(kind="request_started", metadata={"seed": seed})],
                "boundary_coverage": {
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(detected=True),
                    "redis": BoundaryCoverage(),
                },
            },
        )()

    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    replay_results, replay_traces = asyncio.run(
        _run_replay(
            object(),
            "service.app:app",
            [health_scenario, charge_scenario],
            seeds_per_scenario=3,
        )
    )

    assert len(replay_results) == 6
    assert len(replay_traces) == 6
    health_trace = next(trace for trace in replay_traces if trace.path == "/health")
    charge_traces = [trace for trace in replay_traces if trace.path == "/payments/charge"]
    assert health_trace.search_budget is not None
    assert health_trace.search_budget.to_dict() == {
        "requested_seeds": 3,
        "allocated_seeds": 1,
        "redistributed_seeds": -2,
        "allocation_mode": "no_boundary",
        "priority_class": "no_boundary",
        "frontier_capacity": 1,
        "selected_targets": [],
        "planned_fault_kinds": [],
        "scenario_seed_start": 1,
        "scenario_seed_end": 1,
    }
    assert charge_traces[0].search_budget is not None
    assert charge_traces[0].search_budget.to_dict() == {
        "requested_seeds": 3,
        "allocated_seeds": 5,
        "redistributed_seeds": 2,
        "allocation_mode": "target_spread",
        "priority_class": "multi_target",
        "frontier_capacity": 6,
        "selected_targets": ["http", "sqlalchemy"],
        "planned_fault_kinds": ["timeout", "connection_dropped", "connection_refused", "pool_exhausted", "http_error"],
        "scenario_seed_start": 2,
        "scenario_seed_end": 6,
    }
    replay_fault_runs = [run for run in observed_fault_runs if run[1] > 0]
    assert replay_fault_runs == [
        ("/payments/charge", 2, "http", "timeout"),
        ("/payments/charge", 3, "sqlalchemy", "connection_dropped"),
        ("/payments/charge", 4, "http", "connection_refused"),
        ("/payments/charge", 5, "sqlalchemy", "pool_exhausted"),
        ("/payments/charge", 6, "http", "http_error"),
    ]


def test_run_replay_redistributes_only_across_clean_path_replayable_targets(monkeypatch) -> None:
    health_scenario = Scenario(
        method="GET",
        path="/health",
        request=RequestExample(method="GET", path="/health"),
        expected_response=ResponseExample(status_code=200, json={"status": "ok"}),
    )
    charge_scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )

    observed_fault_runs: list[tuple[str, int, str, str]] = []

    class FakeFaultPlan:
        def __init__(self, seed: int, schedule: dict[int, dict[str, str]]) -> None:
            self.seed = seed
            self.schedule = schedule

    def fake_build_fault_plan(
        seed: int,
        *,
        steps: int,
        targets: list[str] | None = None,
        kinds: list[str] | None = None,
    ):
        if steps == 0:
            return FakeFaultPlan(seed, {})
        assert targets is not None
        kind = "timeout" if kinds is None else kinds[0]
        return FakeFaultPlan(seed, {1: {"target": targets[0], "kind": kind}})

    async def fake_run_asgi_app(_app, *, method, path, json_body, seed, fault_plan=None):
        if path == "/health":
            return type(
                "FakeAsgiResult",
                (),
                {
                    "status_code": 200,
                    "body": {"status": "ok"},
                    "trace": [TraceEvent(kind="request_started", metadata={"seed": seed})],
                    "boundary_coverage": {
                        "http": BoundaryCoverage(),
                        "sqlalchemy": BoundaryCoverage(),
                        "redis": BoundaryCoverage(),
                    },
                },
            )()

        scheduled_target = None
        scheduled_kind = None
        if fault_plan is not None and fault_plan.schedule:
            scheduled = fault_plan.schedule[1]
            scheduled_target = scheduled["target"]
            scheduled_kind = scheduled["kind"]

        if seed == 0 and scheduled_target == "http":
            boundary_coverage = {
                "http": BoundaryCoverage(detected=True),
                "sqlalchemy": BoundaryCoverage(),
                "redis": BoundaryCoverage(detected=True),
            }
        elif seed == 0 and scheduled_target == "redis":
            boundary_coverage = {
                "http": BoundaryCoverage(detected=True),
                "sqlalchemy": BoundaryCoverage(),
                "redis": BoundaryCoverage(),
            }
        else:
            boundary_coverage = {
                "http": BoundaryCoverage(detected=True),
                "sqlalchemy": BoundaryCoverage(),
                "redis": BoundaryCoverage(),
            }

        trace = [TraceEvent(kind="request_started", metadata={"seed": seed})]
        if seed > 0 and scheduled_target is not None:
            observed_fault_runs.append((path, seed, scheduled_target, scheduled_kind or "timeout"))
            if scheduled_target == "http":
                trace.append(
                    TraceEvent(
                        kind="fault_injected",
                        metadata={"target": scheduled_target, "fault_kind": scheduled_kind},
                    )
                )

        return type(
            "FakeAsgiResult",
            (),
            {
                "status_code": 200,
                "body": {"status": "charged"},
                "trace": trace,
                "boundary_coverage": boundary_coverage,
            },
        )()

    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    replay_results, replay_traces = asyncio.run(
        _run_replay(
            object(),
            "service.app:app",
            [health_scenario, charge_scenario],
            seeds_per_scenario=3,
        )
    )

    assert len(replay_results) == 5
    assert len(replay_traces) == 5
    charge_traces = [trace for trace in replay_traces if trace.path == "/payments/charge"]
    assert charge_traces[0].search_budget is not None
    assert charge_traces[0].search_budget.to_dict() == {
        "requested_seeds": 3,
        "allocated_seeds": 4,
        "redistributed_seeds": 1,
        "allocation_mode": "target_single",
        "priority_class": "kind_diverse",
        "frontier_capacity": 4,
        "selected_targets": ["http"],
        "planned_fault_kinds": ["timeout", "connection_refused", "http_error", "slow_response"],
        "scenario_seed_start": 2,
        "scenario_seed_end": 5,
    }
    assert observed_fault_runs == [
        ("/payments/charge", 2, "http", "timeout"),
        ("/payments/charge", 3, "http", "connection_refused"),
        ("/payments/charge", 4, "http", "http_error"),
        ("/payments/charge", 5, "http", "slow_response"),
    ]


def test_run_replay_narrows_fault_targets_to_runtime_detected_boundaries(monkeypatch) -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )

    captured_targets: list[list[str]] = []

    class FakeFaultPlan:
        def __init__(self, seed: int) -> None:
            self.seed = seed
            self.schedule = {
                1: {
                    "kind": "fault",
                    "target": "http",
                }
            }

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str], kinds: list[str] | None = None):
        assert steps == 1
        if seed > 0:
            captured_targets.append(list(targets))
        return FakeFaultPlan(seed)

    async def fake_run_asgi_app(_app, *, method, path, json_body, seed, fault_plan=None):
        assert method == "POST"
        assert path == "/payments/charge"
        assert json_body == {"amount": 100}
        return type(
            "FakeAsgiResult",
            (),
            {
                "status_code": 200,
                "body": {"status": "charged"},
                "trace": [TraceEvent(kind="request_started", metadata={"seed": seed})],
                "boundary_coverage": {
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(),
                    "redis": BoundaryCoverage(),
                },
            },
        )()

    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    replay_results, replay_traces = asyncio.run(
        _run_replay(
            object(),
            "service.app:app",
            [scenario],
            seeds_per_scenario=3,
            fault_targets=["http", "redis"],
        )
    )

    assert len(replay_results) == 3
    assert len(replay_traces) == 3
    assert captured_targets == [["http"], ["http"], ["http"]]


def test_run_replay_probes_with_fresh_app_instance_when_root_is_available(monkeypatch, tmp_path: Path) -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        expected_response=ResponseExample(status_code=200, json={"count": 1}),
    )

    @dataclass(slots=True)
    class StatefulApp:
        count: int = 0

    measured_app = StatefulApp()

    class FakeFaultPlan:
        def __init__(self, seed: int) -> None:
            self.seed = seed
            self.schedule = {1: {"kind": "fault", "target": "http"}}

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str], kinds: list[str] | None = None):
        assert steps == 1
        assert targets == ["http"]
        return FakeFaultPlan(seed)

    async def fake_run_asgi_app(app, *, method, path, json_body, seed, fault_plan=None):
        assert method == "POST"
        assert path == "/payments/charge"
        assert json_body == {"amount": 100}
        app.count += 1
        return type(
            "FakeAsgiResult",
            (),
            {
                "status_code": 200,
                "body": {"count": app.count},
                "trace": [TraceEvent(kind="request_started", metadata={"seed": seed, "count": app.count})],
                "boundary_coverage": {
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(),
                    "redis": BoundaryCoverage(),
                },
            },
        )()

    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: StatefulApp())

    replay_results, replay_traces = asyncio.run(
        _run_replay(
            measured_app,
            "service.app:app",
            [scenario],
            seeds_per_scenario=1,
            fault_targets=["http", "redis"],
            root=tmp_path,
        )
    )

    assert len(replay_results) == 1
    assert len(replay_traces) == 1
    assert replay_results[0].changed_response.body == {"count": 1}
    assert measured_app.count == 1


def test_run_replay_uses_single_no_fault_seed_when_no_supported_boundaries_are_detected(monkeypatch) -> None:
    scenario = Scenario(
        method="GET",
        path="/health",
        request=RequestExample(method="GET", path="/health"),
        expected_response=ResponseExample(status_code=200, json={"status": "ok"}),
    )

    observed_runs: list[tuple[int, dict[int, object]]] = []

    async def fake_run_asgi_app(_app, *, method, path, json_body, seed, fault_plan=None):
        assert method == "GET"
        assert path == "/health"
        assert json_body is None
        schedule = {} if fault_plan is None else dict(fault_plan.schedule)
        observed_runs.append((seed, schedule))
        return type(
            "FakeAsgiResult",
            (),
            {
                "status_code": 200,
                "body": {"status": "ok"},
                "trace": [TraceEvent(kind="request_started", metadata={"seed": seed})],
                "boundary_coverage": {
                    "http": BoundaryCoverage(),
                    "sqlalchemy": BoundaryCoverage(),
                    "redis": BoundaryCoverage(),
                },
            },
        )()

    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    replay_results, replay_traces = asyncio.run(
        _run_replay(
            object(),
            "service.app:app",
            [scenario],
            seeds_per_scenario=3,
        )
    )

    assert len(replay_results) == 1
    assert len(replay_traces) == 1
    assert observed_runs == [
        (0, {}),
        (1, {}),
    ]
    assert replay_traces[0].seed == "seed:1"
    assert replay_traces[0].target_selection.to_dict() == {
        "clean_path_targets": [],
        "fault_path_targets": [],
        "selected_targets": [],
        "probe_records": [
            {
                "phase": "clean_path",
                "trigger_target": None,
                "trigger_fault_kind": None,
                "discovered_targets": [],
            }
        ],
        "planned_fault_seed": {
            "seed_value": 1,
            "target": "none",
            "fault_kind": "none",
            "selection_source": "no_boundary",
        },
    }
    assert replay_traces[0].search_budget is not None
    assert replay_traces[0].search_budget.to_dict() == {
        "requested_seeds": 3,
        "allocated_seeds": 1,
        "redistributed_seeds": -2,
        "allocation_mode": "no_boundary",
        "priority_class": "no_boundary",
        "frontier_capacity": 1,
        "selected_targets": [],
        "planned_fault_kinds": [],
        "scenario_seed_start": 1,
        "scenario_seed_end": 1,
    }


def test_scenario_fault_targets_include_fault_only_reachable_redis(monkeypatch, tmp_path: Path) -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"payment_id": "ord-1"}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )

    load_count = 0
    planned_probe_targets: list[str] = []

    class FakeFaultPlan:
        def __init__(self, target: str, kind: str) -> None:
            self.schedule = {
                1: {
                    "target": target,
                    "kind": kind,
                }
            }

    @dataclass(slots=True)
    class FakeAsgiResult:
        status_code: int = 200
        body: dict[str, str] | None = None
        trace: list[TraceEvent] = None  # type: ignore[assignment]
        boundary_coverage: dict[str, BoundaryCoverage] = None  # type: ignore[assignment]

        def __post_init__(self) -> None:
            if self.body is None:
                self.body = {"status": "charged"}
            if self.trace is None:
                self.trace = []
            if self.boundary_coverage is None:
                self.boundary_coverage = {
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(),
                    "redis": BoundaryCoverage(),
                }

    def fake_load_asgi_app(*_args, **_kwargs):
        nonlocal load_count
        load_count += 1
        return object()

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str], kinds: list[str] | None = None):
        assert seed == 0
        assert steps == 1
        assert len(targets) == 1
        planned_probe_targets.append(targets[0])
        return FakeFaultPlan(target=targets[0], kind=kinds[0] if kinds is not None else "timeout")

    async def fake_run_asgi_app(_app, *, fault_plan=None, **_kwargs):
        if fault_plan is None:
            return FakeAsgiResult()
        return FakeAsgiResult(
            boundary_coverage={
                "http": BoundaryCoverage(detected=True),
                "sqlalchemy": BoundaryCoverage(),
                "redis": BoundaryCoverage(detected=True),
            }
        )

    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", fake_load_asgi_app)
    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    targets = asyncio.run(
        _scenario_fault_targets(
            object(),
            "service.app:app",
            scenario,
            ["http", "redis"],
            root=tmp_path,
        )
    )

    assert targets == ["http", "redis"]
    assert planned_probe_targets == ["http", "redis"]
    assert load_count == 3


def test_scenario_fault_targets_include_transitively_fault_reachable_sqlalchemy(
    monkeypatch,
    tmp_path: Path,
) -> None:
    scenario = Scenario(
        method="POST",
        path="/payments/charge",
        request=RequestExample(method="POST", path="/payments/charge", json={"payment_id": "ord-1"}),
        expected_response=ResponseExample(status_code=200, json={"status": "charged"}),
    )

    load_count = 0
    planned_probe_targets: list[str] = []

    class FakeFaultPlan:
        def __init__(self, target: str, kind: str) -> None:
            self.schedule = {
                1: {
                    "target": target,
                    "kind": kind,
                }
            }

    @dataclass(slots=True)
    class FakeAsgiResult:
        status_code: int = 200
        body: dict[str, str] | None = None
        trace: list[TraceEvent] = None  # type: ignore[assignment]
        boundary_coverage: dict[str, BoundaryCoverage] = None  # type: ignore[assignment]

        def __post_init__(self) -> None:
            if self.body is None:
                self.body = {"status": "charged"}
            if self.trace is None:
                self.trace = []
            if self.boundary_coverage is None:
                self.boundary_coverage = {
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(),
                    "redis": BoundaryCoverage(),
                }

    def fake_load_asgi_app(*_args, **_kwargs):
        nonlocal load_count
        load_count += 1
        return object()

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str], kinds: list[str] | None = None):
        assert seed == 0
        assert steps == 1
        assert len(targets) == 1
        planned_probe_targets.append(targets[0])
        return FakeFaultPlan(target=targets[0], kind=kinds[0] if kinds is not None else "timeout")

    async def fake_run_asgi_app(_app, *, fault_plan=None, **_kwargs):
        if fault_plan is None:
            return FakeAsgiResult()

        target = fault_plan.schedule[1]["target"]
        if target == "http":
            return FakeAsgiResult(
                boundary_coverage={
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(),
                    "redis": BoundaryCoverage(detected=True),
                }
            )
        if target == "redis":
            return FakeAsgiResult(
                boundary_coverage={
                    "http": BoundaryCoverage(detected=True),
                    "sqlalchemy": BoundaryCoverage(detected=True),
                    "redis": BoundaryCoverage(detected=True),
                }
            )
        assert target == "sqlalchemy"
        return FakeAsgiResult(
            boundary_coverage={
                "http": BoundaryCoverage(detected=True),
                "sqlalchemy": BoundaryCoverage(detected=True),
                "redis": BoundaryCoverage(detected=True),
            }
        )

    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", fake_load_asgi_app)
    monkeypatch.setattr("litmus.dst.engine.build_fault_plan", fake_build_fault_plan)
    monkeypatch.setattr("litmus.dst.engine.run_asgi_app", fake_run_asgi_app)

    targets = asyncio.run(
        _scenario_fault_targets(
            object(),
            "service.app:app",
            scenario,
            ["http", "redis", "sqlalchemy"],
            root=tmp_path,
        )
    )

    assert targets == ["http", "redis", "sqlalchemy"]
    assert planned_probe_targets == ["http", "redis", "sqlalchemy"]
    assert load_count == 4


def test_fault_targets_for_boundary_coverage_does_not_force_http_without_runtime_detection() -> None:
    targets = _fault_targets_for_boundary_coverage(
        ["http", "redis", "sqlalchemy"],
        {
            "http": BoundaryCoverage(),
            "redis": BoundaryCoverage(detected=True),
            "sqlalchemy": BoundaryCoverage(),
        },
    )

    assert targets == ["redis"]


def test_fault_targets_for_boundary_coverage_returns_empty_when_nothing_is_detected() -> None:
    targets = _fault_targets_for_boundary_coverage(
        ["http", "redis", "sqlalchemy"],
        {
            "http": BoundaryCoverage(),
            "redis": BoundaryCoverage(),
            "sqlalchemy": BoundaryCoverage(),
        },
    )

    assert targets == []


def test_run_verification_keeps_suggested_route_gaps_out_of_replay_scenarios(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "litmus.dst.engine.load_repo_config",
        lambda _root: RepoConfig(app="service.app:app", suggested_invariants=True),
    )
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "litmus.dst.engine._collect_routes",
        lambda _root: [
            RouteDefinition(
                method="POST",
                path="/payments/refund",
                handler_name="refund",
                file_path="service/app.py",
            )
        ],
    )
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])

    captured: dict[str, object] = {}

    def fake_build_scenarios(_routes, invariants):
        captured["scenario_invariants"] = list(invariants)
        return []

    monkeypatch.setattr("litmus.dst.engine.build_scenarios", fake_build_scenarios)
    monkeypatch.setattr("litmus.dst.engine._run_replay", lambda *_args, **_kwargs: asyncio.sleep(0, result=([], [])))
    monkeypatch.setattr("litmus.dst.engine._run_property_checks", lambda *_args, **_kwargs: [])

    result = run_verification(tmp_path)

    assert captured["scenario_invariants"] == []
    assert len(result.invariants) == 1
    assert result.invariants[0].status is InvariantStatus.SUGGESTED
    assert result.scenarios == []


def test_run_verification_loads_curated_suggested_invariants_without_reimporting_stored_confirmed_entries(
    monkeypatch,
    tmp_path: Path,
) -> None:
    mined_confirmed = Invariant(
        name="charge_returns_200",
        source="mined:tests/test_payments.py::test_charge_returns_200",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
        response=ResponseExample(status_code=200, json={"status": "charged"}),
    )
    stored_confirmed = Invariant(
        name="charge_returns_200_from_store",
        source="manual:confirmed",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/charge"),
        response=ResponseExample(status_code=200),
    )
    stored_suggested = Invariant(
        name="refund_needs_review",
        source="manual:suggested",
        status=InvariantStatus.SUGGESTED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/refund"),
        reasoning="Review refund behavior.",
    )

    monkeypatch.setattr(
        "litmus.dst.engine.load_repo_config",
        lambda _root: RepoConfig(app="service.app:app", suggested_invariants=True),
    )
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "litmus.dst.engine._collect_routes",
        lambda _root: [
            RouteDefinition(
                method="POST",
                path="/payments/charge",
                handler_name="charge",
                file_path="service/app.py",
            ),
            RouteDefinition(
                method="POST",
                path="/payments/refund",
                handler_name="refund",
                file_path="service/app.py",
            ),
        ],
    )
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [mined_confirmed])
    monkeypatch.setattr(
        "litmus.dst.engine.default_invariants_path",
        lambda _root: tmp_path / ".litmus" / "invariants.yaml",
    )
    monkeypatch.setattr(
        "litmus.dst.engine.load_invariants",
        lambda _path: [stored_confirmed, stored_suggested],
    )

    captured: dict[str, object] = {}

    def fake_build_scenarios(_routes, invariants):
        captured["scenario_invariants"] = list(invariants)
        return []

    monkeypatch.setattr("litmus.dst.engine.build_scenarios", fake_build_scenarios)
    monkeypatch.setattr("litmus.dst.engine._run_replay", lambda *_args, **_kwargs: asyncio.sleep(0, result=([], [])))
    monkeypatch.setattr("litmus.dst.engine._run_property_checks", lambda *_args, **_kwargs: [])

    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    invariants_path.parent.mkdir(parents=True, exist_ok=True)
    invariants_path.write_text("[]\n", encoding="utf-8")

    result = run_verification(tmp_path)

    assert [invariant.name for invariant in result.invariants] == [
        "charge_returns_200",
        "refund_needs_review",
        "refund_post_payments_refund_needs_confirmed_anchor",
    ]
    assert [invariant.status for invariant in result.invariants] == [
        InvariantStatus.CONFIRMED,
        InvariantStatus.SUGGESTED,
        InvariantStatus.SUGGESTED,
    ]
    assert [invariant.name for invariant in captured["scenario_invariants"]] == ["charge_returns_200"]


def test_run_verification_loads_promoted_curated_confirmed_invariants_into_active_inputs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    promoted_property = Invariant(
        name="refund_is_idempotent",
        source="manual:suggested",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.PROPERTY,
        request=RequestExample(method="POST", path="/payments/refund", json={"refund_id": "r-123"}),
        reasoning="Accepted as a confirmed retry contract.",
        review=InvariantReview(
            state=InvariantReviewState.PROMOTED,
            reason="Reviewed and accepted.",
            reviewed_at="2026-04-06T12:00:00Z",
            review_source="cli",
        ),
    )

    monkeypatch.setattr(
        "litmus.dst.engine.load_repo_config",
        lambda _root: RepoConfig(app="service.app:app", suggested_invariants=True),
    )
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "litmus.dst.engine._collect_routes",
        lambda _root: [
            RouteDefinition(
                method="POST",
                path="/payments/refund",
                handler_name="refund",
                file_path="service/app.py",
            )
        ],
    )
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr(
        "litmus.dst.engine.default_invariants_path",
        lambda _root: tmp_path / ".litmus" / "invariants.yaml",
    )
    monkeypatch.setattr(
        "litmus.dst.engine.load_invariants",
        lambda _path: [promoted_property],
    )

    captured: dict[str, object] = {}

    def fake_build_scenarios(_routes, invariants):
        captured["scenario_invariants"] = list(invariants)
        return []

    def fake_run_property_checks(_app, invariants, *, max_examples: int):
        captured["property_invariants"] = list(invariants)
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine.build_scenarios", fake_build_scenarios)
    monkeypatch.setattr("litmus.dst.engine._run_replay", lambda *_args, **_kwargs: asyncio.sleep(0, result=([], [])))
    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    invariants_path.parent.mkdir(parents=True, exist_ok=True)
    invariants_path.write_text("[]\n", encoding="utf-8")

    result = run_verification(tmp_path)

    assert [invariant.name for invariant in result.invariants] == ["refund_is_idempotent"]
    assert [invariant.name for invariant in captured["scenario_invariants"]] == ["refund_is_idempotent"]
    assert [invariant.name for invariant in captured["property_invariants"]] == ["refund_is_idempotent"]


def test_run_verification_ignores_legacy_promoted_route_gap_records_and_regenerates_warning(
    monkeypatch,
    tmp_path: Path,
) -> None:
    legacy_promoted_route_gap = Invariant(
        name="refund_post_payments_refund_needs_confirmed_anchor",
        source="suggested:route_gap",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/refund"),
        reasoning="Legacy invalid promoted route-gap record.",
        review=InvariantReview(
            state=InvariantReviewState.PROMOTED,
            reason="Legacy bad data.",
            reviewed_at="2026-04-06T12:00:00Z",
            review_source="cli",
        ),
    )

    monkeypatch.setattr(
        "litmus.dst.engine.load_repo_config",
        lambda _root: RepoConfig(app="service.app:app", suggested_invariants=True),
    )
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "litmus.dst.engine._collect_routes",
        lambda _root: [
            RouteDefinition(
                method="POST",
                path="/payments/refund",
                handler_name="refund",
                file_path="service/app.py",
            )
        ],
    )
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr(
        "litmus.dst.engine.default_invariants_path",
        lambda _root: tmp_path / ".litmus" / "invariants.yaml",
    )
    monkeypatch.setattr(
        "litmus.dst.engine.load_invariants",
        lambda _path: [legacy_promoted_route_gap],
    )

    captured: dict[str, object] = {}

    def fake_build_scenarios(_routes, invariants):
        captured["scenario_invariants"] = list(invariants)
        return []

    monkeypatch.setattr("litmus.dst.engine.build_scenarios", fake_build_scenarios)
    monkeypatch.setattr("litmus.dst.engine._run_replay", lambda *_args, **_kwargs: asyncio.sleep(0, result=([], [])))
    monkeypatch.setattr("litmus.dst.engine._run_property_checks", lambda *_args, **_kwargs: [])

    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    invariants_path.parent.mkdir(parents=True, exist_ok=True)
    invariants_path.write_text("[]\n", encoding="utf-8")

    result = run_verification(tmp_path)

    assert [invariant.name for invariant in result.invariants] == [
        "refund_post_payments_refund_needs_confirmed_anchor"
    ]
    assert [invariant.status for invariant in result.invariants] == [InvariantStatus.SUGGESTED]
    assert captured["scenario_invariants"] == []
    assert result.scenarios == []


def test_run_verification_keeps_dismissed_curated_route_gap_suggestions_out_of_active_results_but_still_suppresses_route_gaps(
    monkeypatch,
    tmp_path: Path,
) -> None:
    dismissed_suggested = Invariant(
        name="refund_post_payments_refund_needs_confirmed_anchor",
        source="suggested:route_gap",
        status=InvariantStatus.SUGGESTED,
        type=InvariantType.DIFFERENTIAL,
        request=RequestExample(method="POST", path="/payments/refund"),
        reasoning="Reviewed and intentionally dismissed.",
        review=InvariantReview(
            state=InvariantReviewState.DISMISSED,
            reason="Refund verification is anchored elsewhere.",
            reviewed_at="2026-04-06T12:00:00Z",
            review_source="cli",
        ),
    )

    monkeypatch.setattr(
        "litmus.dst.engine.load_repo_config",
        lambda _root: RepoConfig(app="service.app:app", suggested_invariants=True),
    )
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "litmus.dst.engine._collect_routes",
        lambda _root: [
            RouteDefinition(
                method="POST",
                path="/payments/refund",
                handler_name="refund",
                file_path="service/app.py",
            )
        ],
    )
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr(
        "litmus.dst.engine.default_invariants_path",
        lambda _root: tmp_path / ".litmus" / "invariants.yaml",
    )
    monkeypatch.setattr(
        "litmus.dst.engine.load_invariants",
        lambda _path: [dismissed_suggested],
    )

    captured: dict[str, object] = {}

    def fake_build_scenarios(_routes, invariants):
        captured["scenario_invariants"] = list(invariants)
        return []

    monkeypatch.setattr("litmus.dst.engine.build_scenarios", fake_build_scenarios)
    monkeypatch.setattr("litmus.dst.engine._run_replay", lambda *_args, **_kwargs: asyncio.sleep(0, result=([], [])))
    monkeypatch.setattr("litmus.dst.engine._run_property_checks", lambda *_args, **_kwargs: [])

    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    invariants_path.parent.mkdir(parents=True, exist_ok=True)
    invariants_path.write_text("[]\n", encoding="utf-8")

    result = run_verification(tmp_path)

    assert captured["scenario_invariants"] == []
    assert result.invariants == []
    assert result.scenarios == []


def test_run_verification_exercises_real_property_path_for_passing_invariant(monkeypatch, tmp_path: Path) -> None:
    property_invariant = Invariant(
        name="charge_does_not_5xx",
        source="manual:property",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.PROPERTY,
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 300}),
    )

    monkeypatch.setattr("litmus.dst.engine.load_repo_config", lambda _root: RepoConfig(app="service.app:app"))
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: _PaymentsApp())
    monkeypatch.setattr(
        "litmus.dst.engine._collect_routes",
        lambda _root: [
            RouteDefinition(
                method="POST",
                path="/payments/charge",
                handler_name="charge",
                file_path="service/app.py",
            )
        ],
    )
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [property_invariant])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    result = run_verification(tmp_path)

    assert result.replay_results == []
    assert len(result.property_results) == 1
    property_result = result.property_results[0]
    assert property_result.invariant.name == "charge_does_not_5xx"
    assert property_result.status is PropertyCheckStatus.PASSED
    assert property_result.failing_request is None


def test_run_verification_exercises_real_property_path_for_failing_invariant(monkeypatch, tmp_path: Path) -> None:
    property_invariant = Invariant(
        name="charge_always_returns_200",
        source="manual:property",
        status=InvariantStatus.CONFIRMED,
        type=InvariantType.PROPERTY,
        request=RequestExample(method="POST", path="/payments/charge", json={"amount": 300}),
        response=ResponseExample(status_code=200),
    )

    monkeypatch.setattr("litmus.dst.engine.load_repo_config", lambda _root: RepoConfig(app="service.app:app"))
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: _PaymentsApp())
    monkeypatch.setattr(
        "litmus.dst.engine._collect_routes",
        lambda _root: [
            RouteDefinition(
                method="POST",
                path="/payments/charge",
                handler_name="charge",
                file_path="service/app.py",
            )
        ],
    )
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [property_invariant])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    result = run_verification(tmp_path)

    assert result.replay_results == []
    assert len(result.property_results) == 1
    property_result = result.property_results[0]
    assert property_result.invariant.name == "charge_always_returns_200"
    assert property_result.status is PropertyCheckStatus.FAILED
    assert property_result.failing_request is not None
    assert property_result.failing_request.method == "POST"
    assert property_result.failing_request.path == "/payments/charge"
    assert property_result.failing_request.payload is not None
    assert property_result.failing_request.payload["amount"] > 500


def test_fault_targets_for_loaded_app_detects_sqlalchemy_and_redis_one_module_hop_away(tmp_path: Path) -> None:
    from litmus.discovery.app import load_asgi_app

    _clear_test_modules("service", "sqlalchemy", "redis")
    service_dir = tmp_path / "service"
    sqlalchemy_ext_dir = tmp_path / "sqlalchemy" / "ext"
    redis_dir = tmp_path / "redis"
    service_dir.mkdir()
    sqlalchemy_ext_dir.mkdir(parents=True)
    redis_dir.mkdir()

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "app.py").write_text(
        (
            "from service.db import engine\n"
            "from service.cache import redis_client\n"
            "class FastAPI:\n"
            "    pass\n"
            "app = FastAPI()\n"
        ),
        encoding="utf-8",
    )
    (service_dir / "db.py").write_text(
        (
            "from sqlalchemy.ext.asyncio import create_async_engine\n"
            "engine = create_async_engine('sqlite+aiosqlite:///:memory:')\n"
        ),
        encoding="utf-8",
    )
    (service_dir / "cache.py").write_text(
        (
            "from redis.asyncio import from_url\n"
            "redis_client = from_url('redis://cache')\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "sqlalchemy" / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext_dir / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext_dir / "asyncio.py").write_text(
        (
            "class AsyncSession:\n"
            "    pass\n"
            "def create_async_engine(*args, **kwargs):\n"
            "    return object()\n"
            "def async_sessionmaker(*args, **kwargs):\n"
            "    return object()\n"
        ),
        encoding="utf-8",
    )
    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        (
            "class Redis:\n"
            "    pass\n"
            "class RedisCluster:\n"
            "    pass\n"
            "def from_url(*args, **kwargs):\n"
            "    return object()\n"
        ),
        encoding="utf-8",
    )

    load_asgi_app("service.app:app", tmp_path)

    assert _fault_targets_for_loaded_app("service.app:app", tmp_path) == [
        "http",
        "sqlalchemy",
        "redis",
    ]


def test_boundary_usage_ignores_asyncsession_type_import_when_supported_sqlalchemy_path_is_used(tmp_path: Path) -> None:
    from litmus.discovery.app import load_asgi_app

    _clear_test_modules("service", "sqlalchemy")
    service_dir = tmp_path / "service"
    sqlalchemy_ext_dir = tmp_path / "sqlalchemy" / "ext"
    service_dir.mkdir()
    sqlalchemy_ext_dir.mkdir(parents=True)

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "app.py").write_text(
        (
            "from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine\n"
            "class FastAPI:\n"
            "    pass\n"
            "engine = create_async_engine('sqlite+aiosqlite:///:memory:')\n"
            "SessionLocal = async_sessionmaker(engine, expire_on_commit=False)\n"
            "session_annotation = AsyncSession\n"
            "app = FastAPI()\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "sqlalchemy" / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext_dir / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext_dir / "asyncio.py").write_text(
        (
            "class AsyncSession:\n"
            "    pass\n"
            "def create_async_engine(*args, **kwargs):\n"
            "    return object()\n"
            "def async_sessionmaker(*args, **kwargs):\n"
            "    return object()\n"
        ),
        encoding="utf-8",
    )

    load_asgi_app("service.app:app", tmp_path)

    boundary_usage = _boundary_usage_for_loaded_app("service.app:app", tmp_path)

    assert boundary_usage.supported_targets == ("sqlalchemy",)
    assert boundary_usage.unsupported_targets == ()


def test_fault_targets_ignore_type_only_supported_boundary_imports(tmp_path: Path) -> None:
    from litmus.discovery.app import load_asgi_app

    _clear_test_modules("service", "redis", "sqlalchemy")
    service_dir = tmp_path / "service"
    redis_dir = tmp_path / "redis"
    sqlalchemy_ext_dir = tmp_path / "sqlalchemy" / "ext"
    service_dir.mkdir()
    redis_dir.mkdir()
    sqlalchemy_ext_dir.mkdir(parents=True)

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "app.py").write_text(
        (
            "from redis.asyncio import Redis\n"
            "from sqlalchemy.ext.asyncio import create_async_engine\n"
            "class FastAPI:\n"
            "    pass\n"
            "redis_annotation = Redis\n"
            "engine_factory = create_async_engine\n"
            "app = FastAPI()\n"
        ),
        encoding="utf-8",
    )
    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        (
            "class Redis:\n"
            "    pass\n"
            "def from_url(*args, **kwargs):\n"
            "    return object()\n"
            "class RedisCluster:\n"
            "    pass\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "sqlalchemy" / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext_dir / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext_dir / "asyncio.py").write_text(
        (
            "class AsyncSession:\n"
            "    pass\n"
            "def create_async_engine(*args, **kwargs):\n"
            "    return object()\n"
            "def async_sessionmaker(*args, **kwargs):\n"
            "    return object()\n"
        ),
        encoding="utf-8",
    )

    load_asgi_app("service.app:app", tmp_path)

    boundary_usage = _boundary_usage_for_loaded_app("service.app:app", tmp_path)

    assert boundary_usage.supported_targets == ()
    assert boundary_usage.unsupported_targets == ()
    assert _fault_targets_for_loaded_app("service.app:app", tmp_path) == ["http"]


def test_fault_targets_detect_redis_from_url_via_module_alias(tmp_path: Path) -> None:
    from litmus.discovery.app import load_asgi_app

    _clear_test_modules("service", "redis")
    service_dir = tmp_path / "service"
    redis_dir = tmp_path / "redis"
    service_dir.mkdir()
    redis_dir.mkdir()

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "app.py").write_text(
        (
            "import redis.asyncio as redis\n"
            "class FastAPI:\n"
            "    pass\n"
            'redis_client = redis.Redis.from_url("redis://cache")\n'
            "app = FastAPI()\n"
        ),
        encoding="utf-8",
    )
    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        (
            "class Redis:\n"
            "    @classmethod\n"
            "    def from_url(cls, *args, **kwargs):\n"
            "        return object()\n"
            "def from_url(*args, **kwargs):\n"
            "    return object()\n"
            "class RedisCluster:\n"
            "    pass\n"
        ),
        encoding="utf-8",
    )

    load_asgi_app("service.app:app", tmp_path)

    boundary_usage = _boundary_usage_for_loaded_app("service.app:app", tmp_path)

    assert boundary_usage.supported_targets == ("redis",)
    assert boundary_usage.unsupported_targets == ()
    assert _fault_targets_for_loaded_app("service.app:app", tmp_path) == ["http", "redis"]


def test_fault_targets_detect_redis_from_url_assignment_alias_via_module_alias(tmp_path: Path) -> None:
    from litmus.discovery.app import load_asgi_app

    _clear_test_modules("service", "redis")
    service_dir = tmp_path / "service"
    redis_dir = tmp_path / "redis"
    service_dir.mkdir()
    redis_dir.mkdir()

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "app.py").write_text(
        (
            "import redis.asyncio as redis\n"
            "class FastAPI:\n"
            "    pass\n"
            "RedisFromUrl = redis.Redis.from_url\n"
            'redis_client = RedisFromUrl("redis://cache")\n'
            "app = FastAPI()\n"
        ),
        encoding="utf-8",
    )
    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        (
            "class Redis:\n"
            "    @classmethod\n"
            "    def from_url(cls, *args, **kwargs):\n"
            "        return object()\n"
            "def from_url(*args, **kwargs):\n"
            "    return object()\n"
            "class RedisCluster:\n"
            "    pass\n"
        ),
        encoding="utf-8",
    )

    load_asgi_app("service.app:app", tmp_path)

    boundary_usage = _boundary_usage_for_loaded_app("service.app:app", tmp_path)

    assert boundary_usage.supported_targets == ("redis",)
    assert boundary_usage.unsupported_targets == ()
    assert _fault_targets_for_loaded_app("service.app:app", tmp_path) == ["http", "redis"]


def _clear_test_modules(*prefixes: str) -> None:
    for name in list(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(name, None)
