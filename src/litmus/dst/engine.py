from __future__ import annotations

import asyncio
import ast
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sys

from litmus.config import FaultProfile, RepoConfig, load_repo_config
from litmus.discovery.app import default_app_loader, discover_app_reference
from litmus.discovery.project import iter_python_files
from litmus.discovery.routes import RouteDefinition, extract_routes
from litmus.dst.asgi import run_asgi_app
from litmus.dst.faults import build_fault_plan
from litmus.dst.reachability import (
    PlannedFaultSeed,
    ReachabilityProbeRecord,
    ScenarioReachability,
    TargetSelectionArtifact,
    planned_fault_seed_for_value,
    plan_local_fault_seeds,
    representative_fault_kind_for_target,
)
from litmus.dst.runtime import TraceEvent
from litmus.simulators.boundary_patches import patched_supported_boundaries
from litmus.invariants.mined import mine_invariants_from_tests
from litmus.invariants.models import Invariant, InvariantStatus, InvariantType, RequestExample, ResponseExample
from litmus.invariants.suggested import suggest_route_gap_invariants
from litmus.invariants.store import default_invariants_path, load_invariants
from litmus.properties.runner import PropertyCheckResult, run_property_checks
from litmus.performance import (
    property_max_examples_for_mode,
    replay_seed_count_for_mode,
    search_strategy_for_mode,
)
from litmus.replay.differential import DifferentialReplayResult, run_differential_replay
from litmus.replay.fidelity import (
    normalize_execution_transcript,
    normalize_replay_checkpoints,
    normalize_scheduler_ledger,
)
from litmus.replay.models import ReplayResponseDetails
from litmus.replay.trace import ReplayTraceRecord
from litmus.runs.models import RunMode
from litmus.scenarios.builder import Scenario, build_scenarios
from litmus.search_budget import allocate_scenario_seed_budgets, build_scenario_search_budget
from litmus.verify_scope import VerifyScope, apply_verification_scope, default_verification_scope

LOCAL_PROPERTY_MAX_EXAMPLES = 100
CI_PROPERTY_MAX_EXAMPLES = 500
LOCAL_REPLAY_SEEDS_PER_SCENARIO = 3
CI_REPLAY_SEEDS_PER_SCENARIO = 500
VERIFY_FAULT_TARGETS = ["http", "sqlalchemy", "redis"]
VERIFY_FAULT_KINDS = None
load_asgi_app = default_app_loader().load


@dataclass(slots=True)
class VerificationResult:
    app_reference: str
    routes: list[RouteDefinition]
    invariants: list[Invariant]
    scenarios: list[Scenario]
    replay_results: list[DifferentialReplayResult]
    replay_traces: list[ReplayTraceRecord]
    property_results: list[PropertyCheckResult]
    started_at: str | None = None
    completed_at: str | None = None
    mode: RunMode | str = RunMode.LOCAL
    fault_profile: FaultProfile | str = FaultProfile.DEFAULT
    replay_seeds_per_scenario: int | None = None
    search_strategy: str | None = None
    property_max_examples: int | None = None
    scope_label: str = "full repo"


@dataclass(slots=True)
class VerificationInputs:
    config: RepoConfig
    app_reference: str
    routes: list[RouteDefinition]
    invariants: list[Invariant]
    confirmed_invariants: list[Invariant]
    scenarios: list[Scenario]
    scope_label: str = "full repo"


@dataclass(slots=True, frozen=True)
class AppBoundaryUsage:
    supported_targets: tuple[str, ...] = ()
    unsupported_targets: tuple[str, ...] = ()


def run_verification(
    root: Path | str,
    mode: RunMode | str = RunMode.LOCAL,
    *,
    scope: VerifyScope | None = None,
) -> VerificationResult:
    started_at = datetime.now(UTC).isoformat()
    inputs = collect_verification_inputs(root, scope=scope)
    verification_mode = _coerce_run_mode(mode)
    replay_seed_budget = replay_seed_count_for_mode(
        verification_mode,
        fault_profile=inputs.config.fault_profile,
    )
    replay_search_strategy = search_strategy_for_mode(
        verification_mode,
        fault_profile=inputs.config.fault_profile,
    )
    property_example_budget = property_max_examples_for_mode(
        verification_mode,
        fault_profile=inputs.config.fault_profile,
    )
    with patched_supported_boundaries(Path(root)):
        app = load_asgi_app(inputs.app_reference, Path(root))
        boundary_usage = _boundary_usage_for_loaded_app(inputs.app_reference, Path(root))
        active_fault_targets = _fault_targets_for_loaded_app(inputs.app_reference, Path(root))
        replay_results, replay_traces = asyncio.run(
            _run_replay(
                app,
                inputs.app_reference,
                inputs.scenarios,
                seeds_per_scenario=replay_seed_budget,
                search_strategy=replay_search_strategy,
                fault_targets=active_fault_targets,
                boundary_usage=boundary_usage,
                root=Path(root),
            )
        )
        property_results = _run_property_checks(
            app,
            inputs.confirmed_invariants,
            max_examples=property_example_budget,
        )
    completed_at = datetime.now(UTC).isoformat()
    return VerificationResult(
        scope_label=inputs.scope_label,
        app_reference=inputs.app_reference,
        routes=inputs.routes,
        invariants=inputs.invariants,
        scenarios=inputs.scenarios,
        replay_results=replay_results,
        replay_traces=replay_traces,
        property_results=property_results,
        started_at=started_at,
        completed_at=completed_at,
        mode=verification_mode,
        fault_profile=inputs.config.fault_profile,
        replay_seeds_per_scenario=replay_seed_budget,
        search_strategy=replay_search_strategy,
        property_max_examples=property_example_budget,
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
    curated_promoted_invariants = _load_curated_promoted_invariants(repo_root, discovered_routes)
    curated_suggested_invariants = _load_curated_suggested_invariants(repo_root, discovered_routes)
    routes, scoped_invariants = apply_verification_scope(
        repo_root,
        discovered_routes,
        [*discovered_invariants, *curated_promoted_invariants, *curated_suggested_invariants],
        active_scope,
    )
    confirmed_invariants = [
        invariant for invariant in scoped_invariants if invariant.status is InvariantStatus.CONFIRMED
    ]
    all_curated_suggested_invariants = [
        invariant for invariant in scoped_invariants if invariant.status is InvariantStatus.SUGGESTED
    ]
    curated_suggested_invariants = [
        invariant for invariant in all_curated_suggested_invariants if invariant.is_pending_suggestion()
    ]
    suggested_invariants = _collect_suggested_invariants(
        routes=routes,
        confirmed_invariants=confirmed_invariants,
        curated_suggested_invariants=all_curated_suggested_invariants,
        enabled=config.suggested_invariants,
    )
    invariants = [*confirmed_invariants, *curated_suggested_invariants, *suggested_invariants]
    scenarios = build_scenarios(routes, confirmed_invariants)
    return VerificationInputs(
        config=config,
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

    return suggest_route_gap_invariants(
        endpoints=routes,
        existing_invariants=[*confirmed_invariants, *curated_suggested_invariants],
    )


def _load_curated_suggested_invariants(root: Path | str, routes: list[RouteDefinition]) -> list[Invariant]:
    return _load_curated_invariants_for_routes(
        root,
        routes,
        predicate=lambda invariant: invariant.status is InvariantStatus.SUGGESTED,
    )


def _load_curated_promoted_invariants(root: Path | str, routes: list[RouteDefinition]) -> list[Invariant]:
    return _load_curated_invariants_for_routes(
        root,
        routes,
        predicate=lambda invariant: invariant.is_promoted_confirmation(),
    )


def _load_curated_invariants_for_routes(
    root: Path | str,
    routes: list[RouteDefinition],
    *,
    predicate,
) -> list[Invariant]:
    invariants_path = default_invariants_path(root)
    if not invariants_path.exists():
        return []

    route_keys = {(route.method.upper(), route.path) for route in routes}
    curated_invariants: list[Invariant] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for invariant in load_invariants(invariants_path):
        if not predicate(invariant):
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
        curated_invariants.append(
            invariant.model_copy(update={"request": request.model_copy(update={"method": route_key[0]})})
        )

    return curated_invariants


def _collect_routes(root: Path) -> list[RouteDefinition]:
    routes: list[RouteDefinition] = []
    for python_file in iter_python_files(root):
        routes.extend(extract_routes(python_file, root))
    return routes


def _collect_test_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("test_*.py") if path.is_file())


def _property_max_examples_for_mode(
    mode: RunMode,
    *,
    fault_profile: FaultProfile = FaultProfile.DEFAULT,
) -> int:
    return property_max_examples_for_mode(mode, fault_profile=fault_profile)


def _replay_seed_count_for_mode(
    mode: RunMode,
    *,
    fault_profile: FaultProfile = FaultProfile.DEFAULT,
) -> int:
    return replay_seed_count_for_mode(mode, fault_profile=fault_profile)


async def _run_replay(
    app,
    app_reference: str,
    scenarios: list[Scenario],
    *,
    seeds_per_scenario: int = LOCAL_REPLAY_SEEDS_PER_SCENARIO,
    search_strategy: str = "frontier_first",
    fault_targets: list[str] | None = None,
    boundary_usage: AppBoundaryUsage | None = None,
    root: Path | None = None,
) -> tuple[list[DifferentialReplayResult], list[ReplayTraceRecord]]:
    replay_results: list[DifferentialReplayResult] = []
    replay_traces: list[ReplayTraceRecord] = []
    next_seed_value = 1
    candidate_fault_targets = _normalize_fault_targets(fault_targets or VERIFY_FAULT_TARGETS)
    scenario_reachabilities: list[ScenarioReachability] = []
    for scenario in scenarios:
        reachability = await _scenario_reachability(
            app,
            app_reference,
            scenario,
            candidate_fault_targets,
            root=root,
        )
        scenario_reachabilities.append(reachability)

    scenario_seed_budgets = allocate_scenario_seed_budgets(
        requested_seeds_per_scenario=seeds_per_scenario,
        reachabilities=scenario_reachabilities,
        strategy=search_strategy,
    )

    for scenario, reachability, allocated_seed_budget in zip(
        scenarios,
        scenario_reachabilities,
        scenario_seed_budgets,
        strict=False,
    ):
        planned_fault_seeds = plan_local_fault_seeds(
            seed_start=next_seed_value,
            reachability=reachability,
            seeds_per_scenario=allocated_seed_budget,
        )
        if not planned_fault_seeds and allocated_seed_budget > 0:
            planned_fault_seeds = [
                PlannedFaultSeed(
                    seed_value=next_seed_value,
                    target="none",
                    fault_kind="none",
                    selection_source="no_boundary",
                )
            ]
        scenario_search_budget = build_scenario_search_budget(
            seed_start=next_seed_value,
            requested_seeds=seeds_per_scenario,
            reachability=reachability,
            planned_fault_seeds=planned_fault_seeds,
        )
        for planned_seed in planned_fault_seeds:
            if planned_seed.selection_source == "no_boundary":
                fault_plan = build_fault_plan(
                    seed=planned_seed.seed_value,
                    steps=0,
                )
            else:
                fault_plan = build_fault_plan(
                    seed=planned_seed.seed_value,
                    steps=1,
                    targets=[planned_seed.target],
                    kinds=[planned_seed.fault_kind],
                )
            result = await run_asgi_app(
                app,
                method=scenario.method,
                path=scenario.path,
                json_body=scenario.request.payload,
                seed=planned_seed.seed_value,
                fault_plan=fault_plan,
            )
            trace = [
                *_unsupported_boundary_trace_events(boundary_usage),
                *result.trace,
            ]
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
                        seed=f"seed:{planned_seed.seed_value}",
                        seed_value=planned_seed.seed_value,
                        app_reference=app_reference,
                        method=scenario.method,
                        path=scenario.path,
                        request_payload=scenario.request.payload,
                        baseline_status_code=replay_result.baseline_response.status_code,
                        baseline_body=replay_result.baseline_response.body,
                        trace=trace,
                        scheduler_ledger=normalize_scheduler_ledger(
                            seed=f"seed:{planned_seed.seed_value}",
                            method=scenario.method,
                            path=scenario.path,
                            trace=trace,
                            target_selection=TargetSelectionArtifact.from_reachability(
                                reachability=reachability,
                                planned_fault_seed=planned_seed,
                            ),
                        ),
                        replay_checkpoints=normalize_replay_checkpoints(
                            trace,
                            method=scenario.method,
                            path=scenario.path,
                        ),
                        recorded_outcome=ReplayResponseDetails(
                            status_code=result.status_code,
                            body=result.body,
                        ),
                        execution_transcript=normalize_execution_transcript(trace),
                        target_selection=TargetSelectionArtifact.from_reachability(
                            reachability=reachability,
                            planned_fault_seed=planned_seed,
                        ),
                        search_budget=scenario_search_budget,
                    )
                )
        next_seed_value += len(planned_fault_seeds)

    return replay_results, replay_traces


async def _scenario_fault_targets(
    app,
    app_reference: str,
    scenario: Scenario,
    candidate_targets: list[str],
    *,
    root: Path | None = None,
) -> list[str]:
    reachability = await _scenario_reachability(
        app,
        app_reference,
        scenario,
        candidate_targets,
        root=root,
    )
    return list(reachability.selected_targets)


def replay_target_selection_artifact(
    app,
    app_reference: str,
    scenario: Scenario,
    *,
    seed_value: int,
    scenario_seed_start: int,
    root: Path | None = None,
    candidate_targets: list[str] | None = None,
) -> TargetSelectionArtifact:
    selected_candidate_targets = candidate_targets or VERIFY_FAULT_TARGETS
    reachability = asyncio.run(
        _scenario_reachability(
            app,
            app_reference,
            scenario,
            selected_candidate_targets,
            root=root,
        )
    )
    if reachability.selected_targets:
        planned_seed = planned_fault_seed_for_value(
            seed_start=scenario_seed_start,
            seed_value=seed_value,
            reachability=reachability,
        )
    else:
        planned_seed = PlannedFaultSeed(
            seed_value=seed_value,
            target="none",
            fault_kind="none",
            selection_source="no_boundary",
        )
    return TargetSelectionArtifact.from_reachability(
        reachability=reachability,
        planned_fault_seed=planned_seed,
    )


async def _scenario_reachability(
    app,
    app_reference: str,
    scenario: Scenario,
    candidate_targets: list[str],
    *,
    root: Path | None = None,
) -> ScenarioReachability:
    normalized_targets = _normalize_fault_targets(candidate_targets)
    if not normalized_targets:
        return ScenarioReachability()

    probe_app = app if root is None else load_asgi_app(app_reference, root)
    baseline_result = await run_asgi_app(
        probe_app,
        method=scenario.method,
        path=scenario.path,
        json_body=scenario.request.payload,
        seed=0,
    )
    clean_path_targets = tuple(
        _fault_targets_for_boundary_coverage(
            normalized_targets,
            baseline_result.boundary_coverage,
        )
    )
    probe_records = [
        ReachabilityProbeRecord(
            phase="clean_path",
            discovered_targets=clean_path_targets,
        )
    ]
    fault_path_targets: list[str] = []
    selected_targets = list(clean_path_targets)
    pending_probe_targets = list(clean_path_targets)
    probed_targets: set[str] = set()

    while pending_probe_targets:
        target = pending_probe_targets.pop(0)
        if target in probed_targets:
            continue
        probed_targets.add(target)
        probe_fault_kind = representative_fault_kind_for_target(target)
        probe_app = app if root is None else load_asgi_app(app_reference, root)
        probe_result = await run_asgi_app(
            probe_app,
            method=scenario.method,
            path=scenario.path,
            json_body=scenario.request.payload,
            seed=0,
            fault_plan=build_fault_plan(
                seed=0,
                steps=1,
                targets=[target],
                kinds=[probe_fault_kind],
            ),
        )
        discovered_targets = tuple(
            _fault_targets_for_boundary_coverage(
                normalized_targets,
                probe_result.boundary_coverage,
            )
        )
        probe_records.append(
            ReachabilityProbeRecord(
                phase="fault_path",
                trigger_target=target,
                trigger_fault_kind=probe_fault_kind,
                discovered_targets=discovered_targets,
            )
        )
        for discovered_target in discovered_targets:
            if discovered_target in selected_targets:
                continue
            selected_targets.append(discovered_target)
            if discovered_target not in clean_path_targets:
                fault_path_targets.append(discovered_target)
            if discovered_target not in probed_targets:
                pending_probe_targets.append(discovered_target)

    return ScenarioReachability(
        clean_path_targets=clean_path_targets,
        fault_path_targets=tuple(fault_path_targets),
        selected_targets=tuple(selected_targets),
        probe_records=tuple(probe_records),
    )

def _normalize_fault_targets(targets: list[str]) -> list[str]:
    normalized_targets: list[str] = []
    seen: set[str] = set()
    for target in ["http", *targets]:
        if target in seen:
            continue
        seen.add(target)
        normalized_targets.append(target)
    return normalized_targets


def _fault_targets_for_boundary_coverage(
    candidate_targets: list[str],
    boundary_coverage: dict[str, object],
) -> list[str]:
    active_targets: list[str] = []
    for target in candidate_targets:
        coverage = boundary_coverage.get(target)
        if coverage is None:
            continue
        if getattr(coverage, "detected", False):
            active_targets.append(target)
    return active_targets


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
def _coerce_run_mode(mode: RunMode | str) -> RunMode:
    if isinstance(mode, RunMode):
        return mode

    normalized_mode = mode.strip().lower()
    if normalized_mode == RunMode.LOCAL.value:
        return RunMode.LOCAL
    if normalized_mode == RunMode.CI.value:
        return RunMode.CI
    if normalized_mode == RunMode.MCP.value:
        return RunMode.MCP
    if normalized_mode == RunMode.WATCH.value:
        return RunMode.WATCH
    raise ValueError(f"unsupported verification mode: {mode}")


def _fault_targets_for_loaded_app(reference: str, root: Path) -> list[str]:
    targets = ["http"]
    boundary_usage = _boundary_usage_for_loaded_app(reference, root)
    targets.extend(boundary_usage.supported_targets)
    return targets


def _boundary_usage_for_loaded_app(reference: str, root: Path) -> AppBoundaryUsage:
    _module_name, _separator, _attribute = reference.partition(":")
    module_files = _loaded_repo_module_files(root)
    if not module_files:
        return AppBoundaryUsage()

    supported: set[str] = set()
    unsupported: set[str] = set()

    for module_file in module_files:
        tree = ast.parse(module_file.read_text(encoding="utf-8"))
        module_supported, module_unsupported = _boundary_usage_for_module(tree)
        supported.update(module_supported)
        unsupported.update(module_unsupported)

    return AppBoundaryUsage(
        supported_targets=tuple(
            target
            for target in ("sqlalchemy", "redis")
            if target in supported
        ),
        unsupported_targets=tuple(
            target
            for target in ("sqlalchemy", "redis")
            if target in unsupported
        ),
    )


def _boundary_usage_for_module(tree: ast.AST) -> tuple[set[str], set[str]]:
    supported: set[str] = set()
    unsupported: set[str] = set()
    sqlalchemy_module_aliases: set[str] = set()
    redis_module_aliases: set[str] = set()
    sqlalchemy_symbol_aliases: set[str] = set()
    redis_symbol_aliases: set[str] = set()
    sqlalchemy_factory_aliases: set[str] = set()
    sqlalchemy_engine_builder_aliases: set[str] = set()
    sqlalchemy_engine_aliases: set[str] = set()
    redis_factory_aliases: set[str] = set()
    redis_class_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sqlalchemy.ext.asyncio":
                    sqlalchemy_module_aliases.add(alias.asname or "sqlalchemy.ext.asyncio")
                elif alias.name == "redis.asyncio":
                    redis_module_aliases.add(alias.asname or "redis.asyncio")
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "sqlalchemy.ext.asyncio":
                sqlalchemy_factory_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in {"create_async_engine", "async_sessionmaker"}
                )
                sqlalchemy_engine_builder_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "create_async_engine"
                )
                sqlalchemy_symbol_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "AsyncSession"
                )
            elif node.module == "redis.asyncio":
                redis_factory_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "from_url"
                )
                redis_class_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "Redis"
                )
                redis_symbol_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "RedisCluster"
                )

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            assigned_name = _assignment_target_name(node)
            if assigned_name is None:
                continue
            value_path = _assigned_value_path(node)
            if value_path is None:
                continue
            if _matches_supported_boundary_call(
                value_path,
                direct_path=("sqlalchemy", "ext", "asyncio", "create_async_engine"),
                module_aliases=sqlalchemy_module_aliases,
                symbol_aliases=sqlalchemy_engine_builder_aliases,
                attribute_name="create_async_engine",
            ):
                changed |= _add_alias(sqlalchemy_engine_builder_aliases, assigned_name)
                changed |= _add_alias(sqlalchemy_engine_aliases, assigned_name)
            if _matches_supported_boundary_call(
                value_path,
                direct_path=("sqlalchemy", "ext", "asyncio", "async_sessionmaker"),
                module_aliases=sqlalchemy_module_aliases,
                symbol_aliases=sqlalchemy_factory_aliases,
                attribute_name="async_sessionmaker",
            ):
                changed |= _add_alias(sqlalchemy_factory_aliases, assigned_name)
            if len(value_path) == 1 and value_path[0] in sqlalchemy_engine_aliases:
                changed |= _add_alias(sqlalchemy_engine_aliases, assigned_name)
            if _matches_supported_boundary_call(
                value_path,
                direct_path=("redis", "asyncio", "from_url"),
                module_aliases=redis_module_aliases,
                symbol_aliases=redis_factory_aliases,
                attribute_name="from_url",
            ) or _matches_supported_boundary_call(
                value_path,
                direct_path=("redis", "asyncio", "Redis", "from_url"),
                module_aliases=redis_class_aliases,
                symbol_aliases=redis_factory_aliases,
                attribute_name="from_url",
            ) or _matches_supported_boundary_call(
                value_path,
                direct_path=("redis", "asyncio", "Redis", "from_url"),
                module_aliases=redis_module_aliases,
                symbol_aliases=redis_factory_aliases,
                attribute_name="from_url",
                module_alias_suffix=("Redis", "from_url"),
            ):
                changed |= _add_alias(redis_factory_aliases, assigned_name)
            if _matches_supported_boundary_call(
                value_path,
                direct_path=("redis", "asyncio", "Redis"),
                module_aliases=redis_module_aliases,
                symbol_aliases=redis_class_aliases,
                attribute_name="Redis",
            ):
                changed |= _add_alias(redis_class_aliases, assigned_name)
            if _matches_supported_boundary_call(
                value_path,
                direct_path=("sqlalchemy", "ext", "asyncio", "AsyncSession"),
                module_aliases=sqlalchemy_module_aliases,
                symbol_aliases=sqlalchemy_symbol_aliases,
                attribute_name="AsyncSession",
            ):
                changed |= _add_alias(sqlalchemy_symbol_aliases, assigned_name)
            if _matches_supported_boundary_call(
                value_path,
                direct_path=("redis", "asyncio", "RedisCluster"),
                module_aliases=redis_module_aliases,
                symbol_aliases=redis_symbol_aliases,
                attribute_name="RedisCluster",
            ):
                changed |= _add_alias(redis_symbol_aliases, assigned_name)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_path = _call_path(node.func)
        if call_path is None:
            continue
        if _matches_supported_boundary_call(
            call_path,
            direct_path=("sqlalchemy", "ext", "asyncio", "create_async_engine"),
            module_aliases=sqlalchemy_module_aliases,
            symbol_aliases=sqlalchemy_factory_aliases,
            attribute_name="create_async_engine",
        ) or _matches_supported_boundary_call(
            call_path,
            direct_path=("sqlalchemy", "ext", "asyncio", "async_sessionmaker"),
            module_aliases=sqlalchemy_module_aliases,
            symbol_aliases=sqlalchemy_factory_aliases,
            attribute_name="async_sessionmaker",
        ):
            supported.add("sqlalchemy")
        if _is_supported_asyncsession_constructor_call(
            node,
            call_path=call_path,
            module_aliases=sqlalchemy_module_aliases,
            symbol_aliases=sqlalchemy_symbol_aliases,
            engine_builder_aliases=sqlalchemy_engine_builder_aliases,
            engine_aliases=sqlalchemy_engine_aliases,
        ):
            supported.add("sqlalchemy")
        if _matches_supported_boundary_call(
            call_path,
            direct_path=("redis", "asyncio", "from_url"),
            module_aliases=redis_module_aliases,
            symbol_aliases=redis_factory_aliases,
            attribute_name="from_url",
        ) or _matches_supported_boundary_call(
            call_path,
            direct_path=("redis", "asyncio", "Redis"),
            module_aliases=redis_module_aliases,
            symbol_aliases=redis_class_aliases,
            attribute_name="Redis",
        ) or _matches_supported_boundary_call(
            call_path,
            direct_path=("redis", "asyncio", "Redis", "from_url"),
            module_aliases=redis_class_aliases,
            symbol_aliases=set(),
            attribute_name="from_url",
        ) or _matches_supported_boundary_call(
            call_path,
            direct_path=("redis", "asyncio", "Redis", "from_url"),
            module_aliases=redis_module_aliases,
            symbol_aliases=set(),
            attribute_name="from_url",
            module_alias_suffix=("Redis", "from_url"),
        ):
            supported.add("redis")
        if _matches_supported_boundary_call(
            call_path,
            direct_path=("sqlalchemy", "ext", "asyncio", "AsyncSession"),
            module_aliases=sqlalchemy_module_aliases,
            symbol_aliases=sqlalchemy_symbol_aliases,
            attribute_name="AsyncSession",
        ) and not _is_supported_asyncsession_constructor_call(
            node,
            call_path=call_path,
            module_aliases=sqlalchemy_module_aliases,
            symbol_aliases=sqlalchemy_symbol_aliases,
            engine_builder_aliases=sqlalchemy_engine_builder_aliases,
            engine_aliases=sqlalchemy_engine_aliases,
        ):
            unsupported.add("sqlalchemy")
        if _matches_supported_boundary_call(
            call_path,
            direct_path=("redis", "asyncio", "RedisCluster"),
            module_aliases=redis_module_aliases,
            symbol_aliases=redis_symbol_aliases,
            attribute_name="RedisCluster",
        ):
            unsupported.add("redis")

    return supported, unsupported


def _call_path(node: ast.AST) -> tuple[str, ...] | None:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        parent = _call_path(node.value)
        if parent is None:
            return None
        return (*parent, node.attr)
    return None


def _assignment_target_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _assigned_value_path(node: ast.AST) -> tuple[str, ...] | None:
    if isinstance(node, ast.Assign):
        return _value_path(node.value)
    if isinstance(node, ast.AnnAssign):
        return _value_path(node.value)
    return None


def _value_path(node: ast.AST | None) -> tuple[str, ...] | None:
    if node is None:
        return None
    if isinstance(node, ast.Call):
        return _call_path(node.func)
    return _call_path(node)


def _add_alias(aliases: set[str], alias: str) -> bool:
    if alias in aliases:
        return False
    aliases.add(alias)
    return True


def _matches_supported_boundary_call(
    call_path: tuple[str, ...],
    *,
    direct_path: tuple[str, ...],
    module_aliases: set[str],
    symbol_aliases: set[str],
    attribute_name: str,
    module_alias_suffix: tuple[str, ...] | None = None,
) -> bool:
    if call_path == direct_path:
        return True
    alias_suffix = module_alias_suffix or (attribute_name,)
    if len(call_path) == len(alias_suffix) + 1 and call_path[0] in module_aliases and call_path[1:] == alias_suffix:
        return True
    return len(call_path) == 1 and call_path[0] in symbol_aliases


def _is_supported_asyncsession_constructor_call(
    node: ast.Call,
    *,
    call_path: tuple[str, ...],
    module_aliases: set[str],
    symbol_aliases: set[str],
    engine_builder_aliases: set[str],
    engine_aliases: set[str],
) -> bool:
    if not _matches_supported_boundary_call(
        call_path,
        direct_path=("sqlalchemy", "ext", "asyncio", "AsyncSession"),
        module_aliases=module_aliases,
        symbol_aliases=symbol_aliases,
        attribute_name="AsyncSession",
    ):
        return False

    bind_expression = node.args[0] if node.args else None
    if bind_expression is None:
        for keyword in node.keywords:
            if keyword.arg == "bind":
                bind_expression = keyword.value
                break
    if bind_expression is None:
        return False
    return _is_sqlalchemy_engine_expression(
        bind_expression,
        module_aliases=module_aliases,
        engine_builder_aliases=engine_builder_aliases,
        engine_aliases=engine_aliases,
    )


def _is_sqlalchemy_engine_expression(
    node: ast.AST,
    *,
    module_aliases: set[str],
    engine_builder_aliases: set[str],
    engine_aliases: set[str],
) -> bool:
    if isinstance(node, ast.Name):
        return node.id in engine_aliases
    if isinstance(node, ast.Call):
        call_path = _call_path(node.func)
        if call_path is None:
            return False
        return _matches_supported_boundary_call(
            call_path,
            direct_path=("sqlalchemy", "ext", "asyncio", "create_async_engine"),
            module_aliases=module_aliases,
            symbol_aliases=engine_builder_aliases,
            attribute_name="create_async_engine",
        )
    return False


def _loaded_repo_module_files(root: Path) -> list[Path]:
    repo_root = Path(root).resolve()
    module_files: list[Path] = []
    for module in sys.modules.values():
        module_path = getattr(module, "__file__", None)
        if module_path is None:
            continue
        path = Path(module_path).resolve()
        try:
            path.relative_to(repo_root)
        except ValueError:
            continue
        module_files.append(path)
    return module_files


def _unsupported_boundary_trace_events(boundary_usage: AppBoundaryUsage | None) -> list[TraceEvent]:
    if boundary_usage is None:
        return []

    events: list[TraceEvent] = []
    for boundary in boundary_usage.unsupported_targets:
        detail = "Unsupported constructor or type import in loaded app modules."
        events.append(TraceEvent(kind="boundary_detected", metadata={"boundary": boundary}))
        events.append(
            TraceEvent(
                kind="boundary_unsupported",
                metadata={"boundary": boundary, "detail": detail},
            )
        )
    return events
