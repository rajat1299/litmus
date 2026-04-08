from __future__ import annotations

from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litmus.dst.reachability import PlannedFaultSeed, ScenarioReachability


@dataclass(slots=True, frozen=True)
class ScenarioSearchBudget:
    requested_seeds: int
    allocated_seeds: int
    allocation_mode: str
    selected_targets: tuple[str, ...] = ()
    planned_fault_kinds: tuple[str, ...] = ()
    scenario_seed_start: int | None = None
    scenario_seed_end: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_seeds": self.requested_seeds,
            "allocated_seeds": self.allocated_seeds,
            "allocation_mode": self.allocation_mode,
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
            allocation_mode=str(payload["allocation_mode"]),
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
            "unique_selected_targets": list(self.unique_selected_targets),
            "unique_planned_fault_kinds": list(self.unique_planned_fault_kinds),
            "kind_diverse_scenarios": self.kind_diverse_scenarios,
        }


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
            allocation_mode="disabled",
            selected_targets=tuple(reachability.selected_targets),
            planned_fault_kinds=(),
            scenario_seed_start=None,
            scenario_seed_end=None,
        )

    selected_target_count = len(reachability.selected_targets)
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
        allocation_mode=allocation_mode,
        selected_targets=tuple(reachability.selected_targets),
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
            budget.allocation_mode,
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
