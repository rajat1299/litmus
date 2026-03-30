from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(slots=True, frozen=True)
class DeterministicScheduler:
    seed: int

    def order(self, runnable: list[str]) -> list[str]:
        ordered = list(runnable)
        Random(self.seed).shuffle(ordered)
        return ordered
