from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from litmus.config import load_repo_config
from litmus.discovery.app import discover_app_reference, load_asgi_app
from litmus.discovery.project import iter_python_files
from litmus.discovery.routes import RouteDefinition, extract_routes
from litmus.dst.asgi import run_asgi_app
from litmus.dst.faults import build_fault_plan
from litmus.invariants.mined import mine_invariants_from_tests
from litmus.invariants.models import Invariant, InvariantStatus, InvariantType, RequestExample, ResponseExample
from litmus.invariants.suggested import HeuristicRouteGapSuggestionProvider, suggest_invariants
from litmus.invariants.store import default_invariants_path, load_invariants
from litmus.properties.runner import PropertyCheckResult, run_property_checks
from litmus.replay.differential import DifferentialReplayResult, run_differential_replay
from litmus.replay.trace import ReplayTraceRecord
from litmus.scenarios.builder import Scenario, build_scenarios
from litmus.verify_scope import VerifyScope, apply_verification_scope, default_verification_scope

LOCAL_PROPERTY_MAX_EXAMPLES = 100
CI_PROPERTY_MAX_EXAMPLES = 500
LOCAL_REPLAY_SEEDS_PER_SCENARIO = 3
CI_REPLAY_SEEDS_PER_SCENARIO = 500
VERIFY_FAULT_TARGETS = ["http"]
VERIFY_FAULT_KINDS = ["timeout", "connection_refused", "http_error", "slow_response"]


@dataclass(slots=True)
class VerificationResult:
    app_reference: str
    routes: list[RouteDefinition]
    invariants: list[Invariant]
    scenarios: list[Scenario]
    replay_results: list[DifferentialReplayResult]
    replay_traces: list[ReplayTraceRecord]
    property_results: list[PropertyCheckResult]
    scope_label: str = "full repo"


@dataclass(slots=True)
class VerificationInputs:
    app_reference: str
    routes: list[RouteDefinition]
    invariants: list[Invariant]
    confirmed_invariants: list[Invariant]
    scenarios: list[Scenario]
    scope_label: str = "full repo"


def run_verification(
    root: Path | str,
    mode: str = "local",
    *,
    scope: VerifyScope | None = None,
) -> VerificationResult:
    inputs = collect_verification_inputs(root, scope=scope)
    app = load_asgi_app(inputs.app_reference, Path(root))
    replay_results, replay_traces = asyncio.run(
        _run_replay(
            app,
            inputs.app_reference,
            inputs.scenarios,
            seeds_per_scenario=_replay_seed_count_for_mode(mode),
        )
    )
    property_results = _run_property_checks(
        app,
        inputs.confirmed_invariants,
        max_examples=_property_max_examples_for_mode(mode),
    )
    return VerificationResult(
        scope_label=inputs.scope_label,
        app_reference=inputs.app_reference,
        routes=inputs.routes,
        invariants=inputs.invariants,
        scenarios=inputs.scenarios,
        replay_results=replay_results,
        replay_traces=replay_traces,
        property_results=property_results,
    )


def collect_verification_inputs(
    root: Path | str,
    *,
    scope: VerifyScope | None = None,
) -> VerificationInputs:
    repo_root = Path(root)
    active_scope = scope or default_verification_scope()
    config = load_repo_config(repo_root)
    app_reference = discover_app_reference(repo_root)
    discovered_routes = _collect_routes(repo_root)
    discovered_invariants = mine_invariants_from_tests(_collect_test_files(repo_root))
    curated_suggested_invariants = _load_curated_suggested_invariants(repo_root, discovered_routes)
    routes, scoped_invariants = apply_verification_scope(
        repo_root,
        discovered_routes,
        [*discovered_invariants, *curated_suggested_invariants],
        active_scope,
    )
    confirmed_invariants = [
        invariant for invariant in scoped_invariants if invariant.status is InvariantStatus.CONFIRMED
    ]
    curated_suggested_invariants = [
        invariant for invariant in scoped_invariants if invariant.status is InvariantStatus.SUGGESTED
    ]
    suggested_invariants = _collect_suggested_invariants(
        routes=routes,
        confirmed_invariants=confirmed_invariants,
        curated_suggested_invariants=curated_suggested_invariants,
        enabled=config.suggested_invariants,
    )
    invariants = [*confirmed_invariants, *curated_suggested_invariants, *suggested_invariants]
    scenarios = build_scenarios(routes, confirmed_invariants)
    return VerificationInputs(
        scope_label=active_scope.label,
        app_reference=app_reference,
        routes=routes,
        invariants=invariants,
        confirmed_invariants=confirmed_invariants,
        scenarios=scenarios,
    )


def _collect_suggested_invariants(
    *,
    routes: list[RouteDefinition],
    confirmed_invariants: list[Invariant],
    curated_suggested_invariants: list[Invariant],
    enabled: bool,
) -> list[Invariant]:
    if not enabled:
        return []

    return suggest_invariants(
        provider=HeuristicRouteGapSuggestionProvider(),
        changed_files=[],
        endpoints=routes,
        existing_invariants=[*confirmed_invariants, *curated_suggested_invariants],
    )


def _load_curated_suggested_invariants(root: Path | str, routes: list[RouteDefinition]) -> list[Invariant]:
    invariants_path = default_invariants_path(root)
    if not invariants_path.exists():
        return []

    route_keys = {(route.method.upper(), route.path) for route in routes}
    curated_suggestions: list[Invariant] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for invariant in load_invariants(invariants_path):
        if invariant.status is not InvariantStatus.SUGGESTED:
            continue
        request = invariant.request
        if request is None or request.method is None or request.path is None:
            continue

        route_key = (request.method.upper(), request.path)
        if route_key not in route_keys:
            continue

        identity = (
            invariant.name,
            route_key[0],
            route_key[1],
        )
        if identity in seen_keys:
            continue
        seen_keys.add(identity)
        curated_suggestions.append(invariant.model_copy(update={"request": request.model_copy(update={"method": route_key[0]})}))

    return curated_suggestions


def _collect_routes(root: Path) -> list[RouteDefinition]:
    routes: list[RouteDefinition] = []
    for python_file in iter_python_files(root):
        routes.extend(extract_routes(python_file, root))
    return routes


def _collect_test_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("test_*.py") if path.is_file())


async def _run_replay(
    app,
    app_reference: str,
    scenarios: list[Scenario],
    *,
    seeds_per_scenario: int = LOCAL_REPLAY_SEEDS_PER_SCENARIO,
) -> tuple[list[DifferentialReplayResult], list[ReplayTraceRecord]]:
    replay_results: list[DifferentialReplayResult] = []
    replay_traces: list[ReplayTraceRecord] = []
    next_seed_value = 1

    for scenario in scenarios:
        for _ in range(seeds_per_scenario):
            fault_plan = build_fault_plan(
                seed=next_seed_value,
                steps=1,
                targets=VERIFY_FAULT_TARGETS,
                kinds=VERIFY_FAULT_KINDS,
            )
            result = await run_asgi_app(
                app,
                method=scenario.method,
                path=scenario.path,
                json_body=scenario.request.payload,
                seed=next_seed_value,
                fault_plan=fault_plan,
            )
            changed_response = ResponseExample(
                status_code=result.status_code,
                json=result.body if isinstance(result.body, dict) else None,
            )

            async def runner(_: Scenario) -> ResponseExample:
                return changed_response

            differential_results = await run_differential_replay(scenarios=[scenario], runner=runner)
            if differential_results:
                replay_result = differential_results[0]
                replay_results.append(replay_result)
                replay_traces.append(
                    ReplayTraceRecord(
                        seed=f"seed:{next_seed_value}",
                        seed_value=next_seed_value,
                        app_reference=app_reference,
                        method=scenario.method,
                        path=scenario.path,
                        request_payload=scenario.request.payload,
                        baseline_status_code=replay_result.baseline_response.status_code,
                        baseline_body=replay_result.baseline_response.body,
                        trace=result.trace,
                    )
                )
            next_seed_value += 1

    return replay_results, replay_traces


def _run_property_checks(
    app,
    invariants: list[Invariant],
    *,
    max_examples: int = LOCAL_PROPERTY_MAX_EXAMPLES,
) -> list[PropertyCheckResult]:
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

    return run_property_checks(property_invariants, checker=checker, max_examples=max_examples)


def _property_max_examples_for_mode(mode: str) -> int:
    normalized_mode = _normalize_mode(mode)
    if normalized_mode == "local":
        return LOCAL_PROPERTY_MAX_EXAMPLES
    if normalized_mode == "ci":
        return CI_PROPERTY_MAX_EXAMPLES
    raise AssertionError(f"unreachable verification mode: {normalized_mode}")


def _replay_seed_count_for_mode(mode: str) -> int:
    normalized_mode = _normalize_mode(mode)
    if normalized_mode == "local":
        return LOCAL_REPLAY_SEEDS_PER_SCENARIO
    if normalized_mode == "ci":
        return CI_REPLAY_SEEDS_PER_SCENARIO
    raise AssertionError(f"unreachable verification mode: {normalized_mode}")


def _normalize_mode(mode: str) -> str:
    normalized_mode = mode.strip().lower()
    if normalized_mode in {"local", "ci"}:
        return normalized_mode
    raise ValueError(f"unsupported verification mode: {mode}")
