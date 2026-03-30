from __future__ import annotations

from dataclasses import dataclass, field
import json

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import Invariant, RequestExample, ResponseExample


@dataclass(slots=True)
class Scenario:
    method: str
    path: str
    request: RequestExample
    expected_response: ResponseExample | None = None
    invariants: list[Invariant] = field(default_factory=list)


def build_scenarios(
    routes: list[RouteDefinition],
    invariants: list[Invariant],
) -> list[Scenario]:
    route_keys = {(route.method, route.path) for route in routes}
    scenarios_by_key: dict[tuple[str, str, str], Scenario] = {}

    for invariant in invariants:
        request = invariant.request
        if request is None or request.method is None or request.path is None:
            continue

        route_key = (request.method.upper(), request.path)
        if route_key not in route_keys:
            continue

        scenario_key = (
            route_key[0],
            route_key[1],
            json.dumps(request.payload, sort_keys=True) if request.payload is not None else "null",
        )
        scenario = scenarios_by_key.get(scenario_key)

        if scenario is None:
            scenario = Scenario(
                method=route_key[0],
                path=route_key[1],
                request=request.model_copy(update={"method": route_key[0]}),
                expected_response=invariant.response,
                invariants=[invariant],
            )
            scenarios_by_key[scenario_key] = scenario
            continue

        scenario.invariants.append(invariant)
        if scenario.expected_response is None and invariant.response is not None:
            scenario.expected_response = invariant.response

    return list(scenarios_by_key.values())
