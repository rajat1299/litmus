from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import Invariant, InvariantStatus, InvariantType, RequestExample


@dataclass(slots=True)
class SuggestionContext:
    changed_files: list[str]
    endpoints: list[RouteDefinition]
    existing_invariants: list[Invariant]


class InvariantSuggestionProvider(Protocol):
    def suggest(self, context: SuggestionContext) -> list[Invariant]:
        ...


class HeuristicRouteGapSuggestionProvider:
    def suggest(self, context: SuggestionContext) -> list[Invariant]:
        anchored_routes: set[tuple[str, str]] = set()
        existing_suggested_routes: set[tuple[str, str]] = set()
        for invariant in context.existing_invariants:
            route_key = _route_key(invariant)
            if route_key is None:
                continue
            if invariant.status is InvariantStatus.CONFIRMED:
                anchored_routes.add(route_key)
            elif invariant.status is InvariantStatus.SUGGESTED:
                existing_suggested_routes.add(route_key)

        suggestions: list[Invariant] = []
        seen_routes: set[tuple[str, str]] = set()
        for endpoint in context.endpoints:
            route_key = (endpoint.method.upper(), endpoint.path)
            if route_key in seen_routes:
                continue
            seen_routes.add(route_key)
            if route_key in anchored_routes or route_key in existing_suggested_routes:
                continue
            suggestions.append(
                Invariant(
                    name=_route_gap_name(endpoint),
                    source="suggested:route_gap",
                    status=InvariantStatus.SUGGESTED,
                    type=InvariantType.DIFFERENTIAL,
                    request=RequestExample(method=route_key[0], path=route_key[1]),
                    reasoning=(
                        f"{route_key[0]} {route_key[1]} is selected for verification without a confirmed mined "
                        "invariant anchor. Add or approve a baseline before trusting verification coverage."
                    ),
                )
            )
        return suggestions


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


def _route_key(invariant: Invariant) -> tuple[str, str] | None:
    request = invariant.request
    if request is None or request.method is None or request.path is None:
        return None
    return request.method.upper(), request.path


def _route_gap_name(endpoint: RouteDefinition) -> str:
    normalized_path = endpoint.path.strip("/") or "root"
    normalized_path = re.sub(r"[^a-z0-9]+", "_", normalized_path.lower()).strip("_")
    return f"{endpoint.handler_name}_{endpoint.method.lower()}_{normalized_path}_needs_confirmed_anchor"
