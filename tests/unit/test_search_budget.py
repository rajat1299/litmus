from __future__ import annotations

from litmus.dst.reachability import ScenarioReachability
from litmus.search_budget import (
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
