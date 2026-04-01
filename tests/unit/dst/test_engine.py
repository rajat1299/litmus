from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from litmus.config import RepoConfig
from litmus.dst.engine import _run_replay, run_verification
from litmus.dst.runtime import TraceEvent
from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import Invariant, InvariantStatus, InvariantType, RequestExample, ResponseExample
from litmus.scenarios.builder import Scenario


def test_run_verification_uses_ci_replay_and_property_budgets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    captured: dict[str, int] = {}

    async def fake_run_replay(_app, _app_reference, _scenarios, *, seeds_per_scenario: int):
        captured["seeds_per_scenario"] = seeds_per_scenario
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path, mode="ci")

    assert captured["seeds_per_scenario"] == 500
    assert captured["max_examples"] == 500


def test_run_verification_defaults_to_local_replay_and_property_budgets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    captured: dict[str, int] = {}

    async def fake_run_replay(_app, _app_reference, _scenarios, *, seeds_per_scenario: int):
        captured["seeds_per_scenario"] = seeds_per_scenario
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path)

    assert captured["seeds_per_scenario"] == 3
    assert captured["max_examples"] == 100


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

    captured_fault_plan_seeds: list[int] = []

    class FakeFaultPlan:
        def __init__(self, seed: int) -> None:
            self.seed = seed
            self.schedule = {1: {"kind": "timeout"}}

    def fake_build_fault_plan(seed: int, *, steps: int, targets: list[str], kinds: list[str]):
        assert steps == 1
        assert targets == ["http"]
        assert "timeout" in kinds
        return FakeFaultPlan(seed)

    async def fake_run_asgi_app(_app, *, method, path, json_body, seed, fault_plan):
        assert method == "POST"
        assert path == "/payments/charge"
        assert json_body == {"amount": 100}
        captured_fault_plan_seeds.append(fault_plan.seed)
        return FakeAsgiResult(
            status_code=200,
            body={"status": "charged"},
            trace=[TraceEvent(kind="request_started", metadata={"seed": seed})],
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
    ]
    assert [invariant.status for invariant in result.invariants] == [
        InvariantStatus.CONFIRMED,
        InvariantStatus.SUGGESTED,
    ]
    assert [invariant.name for invariant in captured["scenario_invariants"]] == ["charge_returns_200"]
