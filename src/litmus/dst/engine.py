from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from litmus.discovery.app import discover_app_reference, load_asgi_app
from litmus.discovery.project import iter_python_files
from litmus.discovery.routes import RouteDefinition, extract_routes
from litmus.dst.asgi import run_asgi_app
from litmus.invariants.mined import mine_invariants_from_tests
from litmus.invariants.models import Invariant, InvariantType, RequestExample, ResponseExample
from litmus.properties.runner import PropertyCheckResult, run_property_checks
from litmus.replay.differential import DifferentialReplayResult, run_differential_replay
from litmus.scenarios.builder import Scenario, build_scenarios


@dataclass(slots=True)
class VerificationResult:
    app_reference: str
    routes: list[RouteDefinition]
    invariants: list[Invariant]
    scenarios: list[Scenario]
    replay_results: list[DifferentialReplayResult]
    property_results: list[PropertyCheckResult]


def run_verification(root: Path | str) -> VerificationResult:
    repo_root = Path(root)
    app_reference = discover_app_reference(repo_root)
    app = load_asgi_app(app_reference, repo_root)
    routes = _collect_routes(repo_root)
    invariants = mine_invariants_from_tests(_collect_test_files(repo_root))
    scenarios = build_scenarios(routes, invariants)
    replay_results = asyncio.run(_run_replay(app, scenarios))
    property_results = _run_property_checks(app, invariants)
    return VerificationResult(
        app_reference=app_reference,
        routes=routes,
        invariants=invariants,
        scenarios=scenarios,
        replay_results=replay_results,
        property_results=property_results,
    )


def _collect_routes(root: Path) -> list[RouteDefinition]:
    routes: list[RouteDefinition] = []
    for python_file in iter_python_files(root):
        routes.extend(extract_routes(python_file, root))
    return routes


def _collect_test_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("test_*.py") if path.is_file())


async def _run_replay(app, scenarios: list[Scenario]) -> list[DifferentialReplayResult]:
    async def runner(scenario: Scenario) -> ResponseExample:
        result = await run_asgi_app(
            app,
            method=scenario.method,
            path=scenario.path,
            json_body=scenario.request.payload,
        )
        return ResponseExample(status_code=result.status_code, json=result.body if isinstance(result.body, dict) else None)

    return await run_differential_replay(scenarios=scenarios, runner=runner)


def _run_property_checks(app, invariants: list[Invariant]) -> list[PropertyCheckResult]:
    property_invariants = [invariant for invariant in invariants if invariant.type is InvariantType.PROPERTY]

    def checker(invariant: Invariant, request: RequestExample) -> bool:
        result = asyncio.run(
            run_asgi_app(
                app,
                method=request.method or "GET",
                path=request.path or "/",
                json_body=request.payload,
            )
        )

        if invariant.response is None:
            return result.status_code < 500

        if invariant.response.status_code is not None and result.status_code != invariant.response.status_code:
            return False

        if invariant.response.body is not None and result.body != invariant.response.body:
            return False

        return True

    return run_property_checks(property_invariants, checker=checker)
