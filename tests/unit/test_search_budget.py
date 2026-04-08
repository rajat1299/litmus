from __future__ import annotations

from litmus.dst.reachability import ScenarioReachability
from litmus.search_budget import (
    ScenarioSearchBudget,
    allocate_scenario_seed_budgets,
    frontier_capacity,
    scenario_priority_class,
)


def test_search_budget_helpers_classify_replayable_frontier() -> None:
    multi_target = ScenarioReachability(
        clean_path_targets=("http", "sqlalchemy"),
        fault_path_targets=("redis",),
        selected_targets=("http", "sqlalchemy", "redis"),
    )
    kind_diverse = ScenarioReachability(
        clean_path_targets=("http",),
        fault_path_targets=("redis",),
        selected_targets=("http", "redis"),
    )
    no_boundary = ScenarioReachability(
        clean_path_targets=(),
        fault_path_targets=("redis",),
        selected_targets=("redis",),
    )

    assert scenario_priority_class(multi_target) == "multi_target"
    assert frontier_capacity(multi_target) == 6
    assert scenario_priority_class(kind_diverse) == "kind_diverse"
    assert frontier_capacity(kind_diverse) == 4
    assert scenario_priority_class(no_boundary) == "no_boundary"
    assert frontier_capacity(no_boundary) == 1


def test_allocate_scenario_seed_budgets_prioritizes_multi_target_frontier() -> None:
    reachabilities = [
        ScenarioReachability(
            clean_path_targets=("http", "sqlalchemy"),
            selected_targets=("http", "sqlalchemy"),
        ),
        ScenarioReachability(
            clean_path_targets=("http",),
            selected_targets=("http",),
        ),
        ScenarioReachability(),
    ]

    assert allocate_scenario_seed_budgets(
        requested_seeds_per_scenario=3,
        reachabilities=reachabilities,
    ) == [5, 3, 1]


def test_scenario_search_budget_restores_legacy_frontier_conservatively() -> None:
    legacy_kind_diverse_payload = {
        "requested_seeds": 500,
        "allocated_seeds": 500,
        "redistributed_seeds": 0,
        "allocation_mode": "target_single",
        "selected_targets": ["redis"],
        "planned_fault_kinds": ["timeout", "connection_refused", "moved"],
        "scenario_seed_start": 1,
        "scenario_seed_end": 500,
    }

    restored_kind_diverse = ScenarioSearchBudget.from_dict(legacy_kind_diverse_payload)

    assert restored_kind_diverse.priority_class == "kind_diverse"
    assert restored_kind_diverse.frontier_capacity == 3

    legacy_multi_target_payload = {
        "requested_seeds": 3,
        "allocated_seeds": 3,
        "redistributed_seeds": 0,
        "allocation_mode": "target_spread",
        "selected_targets": ["http", "sqlalchemy", "redis"],
        "planned_fault_kinds": ["timeout", "connection_dropped"],
        "scenario_seed_start": 1,
        "scenario_seed_end": 3,
    }

    restored_multi_target = ScenarioSearchBudget.from_dict(legacy_multi_target_payload)

    assert restored_multi_target.priority_class == "multi_target"
    assert restored_multi_target.frontier_capacity == 3

    legacy_no_boundary_payload = {
        "requested_seeds": 3,
        "allocated_seeds": 1,
        "redistributed_seeds": -2,
        "allocation_mode": "no_boundary",
        "selected_targets": [],
        "planned_fault_kinds": [],
        "scenario_seed_start": 1,
        "scenario_seed_end": 1,
    }

    restored_no_boundary = ScenarioSearchBudget.from_dict(legacy_no_boundary_payload)

    assert restored_no_boundary.priority_class == "no_boundary"
    assert restored_no_boundary.frontier_capacity == 1
