from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Any

DEFAULT_FAULT_KINDS_BY_TARGET: dict[str, list[str]] = {
    "http": ["timeout", "connection_refused", "http_error", "slow_response"],
    "sqlalchemy": ["connection_dropped", "pool_exhausted"],
    "redis": ["timeout", "connection_refused", "partial_write", "moved"],
}


@dataclass(slots=True, frozen=True)
class FaultSpec:
    kind: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FaultPlan:
    seed: int
    schedule: dict[int, FaultSpec] = field(default_factory=dict)

    def fault_for_step(self, step: int) -> FaultSpec | None:
        return self.schedule.get(step)


def build_fault_plan(
    seed: int,
    steps: int,
    targets: list[str] | None = None,
    kinds: list[str] | None = None,
) -> FaultPlan:
    if steps <= 0:
        return FaultPlan(seed=seed)

    available_targets = targets or ["http"]
    available_kinds = kinds or ["timeout"]
    rng = Random(seed)
    event_count = min(steps, max(1, min(len(available_targets), len(available_kinds))))
    selected_steps = sorted(rng.sample(range(1, steps + 1), k=event_count))
    schedule: dict[int, FaultSpec] = {}
    for index, step in enumerate(selected_steps):
        cycle_index = ((seed - 1) // max(1, len(available_targets))) + index
        if kinds is not None:
            target = available_targets[(seed + index - 1) % len(available_targets)]
            kind = available_kinds[cycle_index % len(available_kinds)]
        else:
            target = available_targets[(seed + index - 1) % len(available_targets)]
            target_kinds = DEFAULT_FAULT_KINDS_BY_TARGET.get(target, ["timeout"])
            kind = target_kinds[cycle_index % len(target_kinds)]
        schedule[step] = FaultSpec(kind=kind, target=target)
    return FaultPlan(seed=seed, schedule=schedule)
