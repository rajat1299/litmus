from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import Invariant, InvariantStatus


@dataclass(slots=True)
class SuggestionContext:
    changed_files: list[str]
    endpoints: list[RouteDefinition]
    existing_invariants: list[Invariant]


class InvariantSuggestionProvider(Protocol):
    def suggest(self, context: SuggestionContext) -> list[Invariant]:
        ...


def suggest_invariants(
    provider: InvariantSuggestionProvider,
    changed_files: list[str],
    endpoints: list[RouteDefinition],
    existing_invariants: list[Invariant],
) -> list[Invariant]:
    context = SuggestionContext(
        changed_files=list(changed_files),
        endpoints=list(endpoints),
        existing_invariants=list(existing_invariants),
    )
    suggestions = provider.suggest(context)

    return [
        suggestion.model_copy(update={"status": InvariantStatus.SUGGESTED})
        for suggestion in suggestions
    ]
