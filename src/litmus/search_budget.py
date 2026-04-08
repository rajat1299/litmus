from __future__ import annotations

from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litmus.dst.reachability import PlannedFaultSeed, ScenarioReachability
else:
    from litmus.dst.reachability import planned_target_fault_pairs, replayable_targets


@dataclass(slots=True, frozen=True)
class ScenarioSearchBudget:
    requested_seeds: int
    allocated_seeds: int
    redistributed_seeds: int
    allocation_mode: str
    priority_class: str = "no_boundary"
    frontier_capacity: int = 0
    selected_targets: tuple[str, ...] = ()
    planned_fault_kinds: tuple[str, ...] = ()
    scenario_seed_start: int | None = None
    scenario_seed_end: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_seeds": self.requested_seeds,
            "allocated_seeds": self.allocated_seeds,
            "redistributed_seeds": self.redistributed_seeds,
            "allocation_mode": self.allocation_mode,
            "priority_class": self.priority_class,
            "frontier_capacity": self.frontier_capacity,
            "selected_targets": list(self.selected_targets),
            "planned_fault_kinds": list(self.planned_fault_kinds),
            "scenario_seed_start": self.scenario_seed_start,
            "scenario_seed_end": self.scenario_seed_end,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ScenarioSearchBudget:
        return cls(
            requested_seeds=int(payload["requested_seeds"]),
            allocated_seeds=int(payload["allocated_seeds"]),
            redistributed_seeds=int(payload.get("redistributed_seeds", 0)),
            allocation_mode=str(payload["allocation_mode"]),
            priority_class=str(payload.get("priority_class", _legacy_priority_class(payload))),
            frontier_capacity=int(payload.get("frontier_capacity", _legacy_frontier_capacity(payload))),
            selected_targets=tuple(str(target) for target in payload.get("selected_targets", [])),
            planned_fault_kinds=tuple(str(kind) for kind in payload.get("planned_fault_kinds", [])),
            scenario_seed_start=(
                None if payload.get("scenario_seed_start") is None else int(payload["scenario_seed_start"])
            ),
            scenario_seed_end=None if payload.get("scenario_seed_end") is None else int(payload["scenario_seed_end"]),
        )


@dataclass(slots=True, frozen=True)
class SearchBudgetSummary:
    requested_seeds_per_scenario: int
    requested_total_replay_seeds: int
    allocated_total_replay_seeds: int
    executed_replays: int
    scenarios_with_reachable_targets: int
    scenarios_without_reachable_targets: int
    target_single_scenarios: int
    target_spread_scenarios: int
    no_boundary_scenarios: int
    disabled_scenarios: int
    reduced_allocation_scenarios: int
    redistributed_scenarios: int
    frontier_capped_scenarios: int
    multi_target_priority_scenarios: int
    kind_diverse_priority_scenarios: int
    unique_selected_targets: tuple[str, ...] = ()
    unique_planned_fault_kinds: tuple[str, ...] = ()
    kind_diverse_scenarios: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_seeds_per_scenario": self.requested_seeds_per_scenario,
            "requested_total_replay_seeds": self.requested_total_replay_seeds,
            "allocated_total_replay_seeds": self.allocated_total_replay_seeds,
            "executed_replays": self.executed_replays,
            "scenarios_with_reachable_targets": self.scenarios_with_reachable_targets,
            "scenarios_without_reachable_targets": self.scenarios_without_reachable_targets,
            "target_single_scenarios": self.target_single_scenarios,
            "target_spread_scenarios": self.target_spread_scenarios,
            "no_boundary_scenarios": self.no_boundary_scenarios,
            "disabled_scenarios": self.disabled_scenarios,
            "reduced_allocation_scenarios": self.reduced_allocation_scenarios,
            "redistributed_scenarios": self.redistributed_scenarios,
            "frontier_capped_scenarios": self.frontier_capped_scenarios,
            "multi_target_priority_scenarios": self.multi_target_priority_scenarios,
            "kind_diverse_priority_scenarios": self.kind_diverse_priority_scenarios,
            "unique_selected_targets": list(self.unique_selected_targets),
            "unique_planned_fault_kinds": list(self.unique_planned_fault_kinds),
            "kind_diverse_scenarios": self.kind_diverse_scenarios,
        }


def allocate_scenario_seed_budgets(
    *,
    requested_seeds_per_scenario: int,
    reachabilities: list[ScenarioReachability],
) -> list[int]:
    if requested_seeds_per_scenario <= 0:
        return [0 for _ in reachabilities]

    capacities = [frontier_capacity(reachability) for reachability in reachabilities]
    priority_classes = [scenario_priority_class(reachability) for reachability in reachabilities]
    allocations = [min(requested_seeds_per_scenario, capacity) for capacity in capacities]
    remaining_budget = requested_seeds_per_scenario * len(reachabilities) - sum(allocations)

    while remaining_budget > 0:
        candidate_indices = [
            index
            for index, (allocation, capacity) in enumerate(zip(allocations, capacities))
            if allocation < capacity
        ]
        if not candidate_indices:
            break

        chosen_index = max(
            candidate_indices,
            key=lambda index: (
                _priority_rank(priority_classes[index]),
                capacities[index] - allocations[index],
                capacities[index],
                len(replayable_targets(reachabilities[index])),
                -index,
            ),
        )
        allocations[chosen_index] += 1
        remaining_budget -= 1

    return allocations


def frontier_capacity(reachability: ScenarioReachability) -> int:
    if not reachability.selected_targets:
        return 1
    replayable_pairs = planned_target_fault_pairs(reachability)
    if not replayable_pairs:
        return 1
    return len(replayable_pairs)


def scenario_priority_class(reachability: ScenarioReachability) -> str:
    replayable = replayable_targets(reachability)
    if not replayable:
        return "no_boundary"
    if len(replayable) > 1:
        return "multi_target"
    if len(planned_target_fault_pairs(reachability)) > 1:
        return "kind_diverse"
    return "single_target"


def build_scenario_search_budget(
    *,
    seed_start: int,
    requested_seeds: int,
    reachability: ScenarioReachability,
    planned_fault_seeds: list[PlannedFaultSeed],
) -> ScenarioSearchBudget:
    if requested_seeds <= 0:
        return ScenarioSearchBudget(
            requested_seeds=requested_seeds,
            allocated_seeds=0,
            redistributed_seeds=0,
            allocation_mode="disabled",
            priority_class="disabled",
            frontier_capacity=0,
            selected_targets=tuple(reachability.selected_targets),
            planned_fault_kinds=(),
            scenario_seed_start=None,
            scenario_seed_end=None,
        )

    selected_targets = tuple(
        dict.fromkeys(
            planned_seed.target
            for planned_seed in planned_fault_seeds
            if planned_seed.target != "none"
        )
    )
    selected_target_count = len(selected_targets)
    if selected_target_count == 0:
        allocation_mode = "no_boundary"
    elif selected_target_count == 1:
        allocation_mode = "target_single"
    else:
        allocation_mode = "target_spread"
    allocated_seeds = len(planned_fault_seeds)
    if planned_fault_seeds:
        scenario_seed_start = planned_fault_seeds[0].seed_value
        scenario_seed_end = planned_fault_seeds[-1].seed_value
    else:
        scenario_seed_start = seed_start
        scenario_seed_end = None

    return ScenarioSearchBudget(
        requested_seeds=requested_seeds,
        allocated_seeds=allocated_seeds,
        redistributed_seeds=allocated_seeds - requested_seeds,
        allocation_mode=allocation_mode,
        priority_class=scenario_priority_class(reachability),
        frontier_capacity=frontier_capacity(reachability),
        selected_targets=selected_targets,
        planned_fault_kinds=tuple(
            dict.fromkeys(
                planned_seed.fault_kind
                for planned_seed in planned_fault_seeds
                if planned_seed.fault_kind != "none"
            )
        ),
        scenario_seed_start=scenario_seed_start,
        scenario_seed_end=scenario_seed_end,
    )


def summarize_search_budget(
    *,
    scenario_count: int,
    requested_seeds_per_scenario: int,
    replay_traces: list[object],
) -> SearchBudgetSummary:
    scenario_budgets = _unique_scenario_budgets(replay_traces)
    unique_selected_targets = tuple(
        sorted({target for budget in scenario_budgets for target in budget.selected_targets})
    )
    unique_planned_fault_kinds = tuple(
        sorted({kind for budget in scenario_budgets for kind in budget.planned_fault_kinds})
    )
    if not scenario_budgets:
        return SearchBudgetSummary(
            requested_seeds_per_scenario=requested_seeds_per_scenario,
            requested_total_replay_seeds=scenario_count * requested_seeds_per_scenario,
            allocated_total_replay_seeds=len(replay_traces),
            executed_replays=len(replay_traces),
            scenarios_with_reachable_targets=0,
            scenarios_without_reachable_targets=0,
            target_single_scenarios=0,
            target_spread_scenarios=0,
            no_boundary_scenarios=0,
            disabled_scenarios=0,
            reduced_allocation_scenarios=0,
            redistributed_scenarios=0,
            frontier_capped_scenarios=0,
            multi_target_priority_scenarios=0,
            kind_diverse_priority_scenarios=0,
            unique_selected_targets=(),
            unique_planned_fault_kinds=(),
            kind_diverse_scenarios=0,
        )

    return SearchBudgetSummary(
        requested_seeds_per_scenario=requested_seeds_per_scenario,
        requested_total_replay_seeds=scenario_count * requested_seeds_per_scenario,
        allocated_total_replay_seeds=sum(budget.allocated_seeds for budget in scenario_budgets),
        executed_replays=len(replay_traces),
        scenarios_with_reachable_targets=sum(1 for budget in scenario_budgets if budget.selected_targets),
        scenarios_without_reachable_targets=sum(1 for budget in scenario_budgets if not budget.selected_targets),
        target_single_scenarios=sum(1 for budget in scenario_budgets if budget.allocation_mode == "target_single"),
        target_spread_scenarios=sum(1 for budget in scenario_budgets if budget.allocation_mode == "target_spread"),
        no_boundary_scenarios=sum(1 for budget in scenario_budgets if budget.allocation_mode == "no_boundary"),
        disabled_scenarios=sum(1 for budget in scenario_budgets if budget.allocation_mode == "disabled"),
        reduced_allocation_scenarios=sum(
            1 for budget in scenario_budgets if budget.allocated_seeds < budget.requested_seeds
        ),
        redistributed_scenarios=sum(1 for budget in scenario_budgets if budget.redistributed_seeds != 0),
        frontier_capped_scenarios=sum(
            1 for budget in scenario_budgets if budget.frontier_capacity > 0 and budget.allocated_seeds >= budget.frontier_capacity
        ),
        multi_target_priority_scenarios=sum(
            1 for budget in scenario_budgets if budget.priority_class == "multi_target"
        ),
        kind_diverse_priority_scenarios=sum(
            1 for budget in scenario_budgets if budget.priority_class == "kind_diverse"
        ),
        unique_selected_targets=unique_selected_targets,
        unique_planned_fault_kinds=unique_planned_fault_kinds,
        kind_diverse_scenarios=sum(1 for budget in scenario_budgets if len(budget.planned_fault_kinds) > 1),
    )


def _unique_scenario_budgets(replay_traces: list[object]) -> list[ScenarioSearchBudget]:
    budgets: list[ScenarioSearchBudget] = []
    seen_keys: set[tuple[object, ...]] = set()

    for record in replay_traces:
        budget = getattr(record, "search_budget", None)
        if budget is None:
            continue
        record_request_payload = getattr(record, "request_payload", None)
        request_key = json.dumps(record_request_payload, sort_keys=True) if record_request_payload is not None else None
        key = (
            getattr(record, "method", None),
            getattr(record, "path", None),
            request_key,
            budget.requested_seeds,
            budget.allocated_seeds,
            budget.redistributed_seeds,
            budget.allocation_mode,
            budget.priority_class,
            budget.frontier_capacity,
            budget.scenario_seed_start,
            budget.scenario_seed_end,
            budget.selected_targets,
            budget.planned_fault_kinds,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        budgets.append(budget)

    return budgets


def _priority_rank(priority_class: str) -> int:
    return {
        "multi_target": 3,
        "kind_diverse": 2,
        "single_target": 1,
        "no_boundary": 0,
        "disabled": -1,
    }.get(priority_class, -1)


def _legacy_priority_class(payload: dict[str, object]) -> str:
    allocation_mode = str(payload.get("allocation_mode", "no_boundary"))
    selected_targets = tuple(str(target) for target in payload.get("selected_targets", []))
    planned_fault_kinds = tuple(str(kind) for kind in payload.get("planned_fault_kinds", []))
    if allocation_mode == "disabled":
        return "disabled"
    if not selected_targets:
        return "no_boundary"
    if len(selected_targets) > 1:
        return "multi_target"
    if len(planned_fault_kinds) > 1:
        return "kind_diverse"
    return "single_target"


def _legacy_frontier_capacity(payload: dict[str, object]) -> int:
    allocated_seeds = int(payload.get("allocated_seeds", 0))
    selected_targets = tuple(str(target) for target in payload.get("selected_targets", []))
    planned_fault_kinds = tuple(str(kind) for kind in payload.get("planned_fault_kinds", []))
    if not selected_targets and allocated_seeds == 0:
        return 0
    return max(allocated_seeds, len(planned_fault_kinds), 1)
