from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Any


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

    schedule = {
        step: FaultSpec(
            kind=rng.choice(available_kinds),
            target=rng.choice(available_targets),
        )
        for step in selected_steps
    }
    return FaultPlan(seed=seed, schedule=schedule)
