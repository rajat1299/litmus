from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from litmus.compatibility import compatibility_report_from_result
from litmus.discovery.app import default_app_loader
from litmus.dst.asgi import run_asgi_app
from litmus.dst.engine import (
    _boundary_usage_for_loaded_app,
    _unsupported_boundary_trace_events,
    collect_verification_inputs,
    replay_target_selection_artifact,
    run_verification,
)
from litmus.invariants.models import RequestExample, ResponseExample
from litmus.mcp.types import (
    BoundaryCoverageCounts,
    ExplainFailureOperationResult,
    InvariantCounts,
    InvariantView,
    ListInvariantsOperationResult,
    PerformanceCounts,
    PropertyCounts,
    ReplayCounts,
    ReplayOperationResult,
    VerifyOperationResult,
)
from litmus.replay.differential import ReplayClassification, run_differential_replay
from litmus.replay.explain import explain_replay
from litmus.replay.fidelity import (
    compare_replay_contract,
    normalize_execution_transcript,
    normalize_replay_checkpoints,
    normalize_scheduler_ledger,
)
from litmus.replay.models import ReplayExplanation, ReplayResponseDetails
from litmus.replay.trace import boundary_coverage_from_result, replay_fault_plan
from litmus.simulators.boundary_patches import patched_supported_boundaries
from litmus.runs import RunMode, record_replay_run, record_verification_run, replay_record_for_seed
from litmus.runs.summary import VerificationProjection
from litmus.scenarios.builder import Scenario
from litmus.verify_scope import VerifyScope, resolve_verification_scope


def run_verify_operation(
    root: Path | str,
    *,
    target: Path | str | None = None,
    staged: bool = False,
    diff: str | None = None,
    mode: RunMode = RunMode.MCP,
) -> VerifyOperationResult:
    repo_root = Path(root)
    scope = _resolve_scope(repo_root, target=target, staged=staged, diff=diff)
    result = run_verification(repo_root, mode=mode, scope=scope)
    run = record_verification_run(repo_root, result, mode=mode)
    projection = VerificationProjection.from_result(result)
    pending_review = sum(1 for invariant in result.invariants if invariant.is_pending_suggestion())
    return VerifyOperationResult(
        run_id=run.run_id,
        app_reference=projection.app_reference,
        scope_label=projection.scope_label,
        routes=projection.routes,
        invariants=InvariantCounts(**projection.invariants, pending_review=pending_review),
        scenarios=projection.scenarios,
        replay=ReplayCounts(
            unchanged=projection.replay["unchanged"],
            breaking=projection.replay["breaking_change"],
            benign=projection.replay["benign_change"],
            improvement=projection.replay["improvement"],
        ),
        properties=PropertyCounts(**projection.properties),
        performance=PerformanceCounts(**projection.performance),
        boundary_coverage=BoundaryCoverageCounts.from_mapping(boundary_coverage_from_result(result)),
        compatibility=compatibility_report_from_result(result),
        replay_seeds=[record.seed for record in result.replay_traces],
    )


def run_list_invariants_operation(
    root: Path | str,
    *,
    target: Path | str | None = None,
    staged: bool = False,
    diff: str | None = None,
) -> ListInvariantsOperationResult:
    repo_root = Path(root)
    scope = _resolve_scope(repo_root, target=target, staged=staged, diff=diff)
    inputs = collect_verification_inputs(repo_root, scope=scope)
    invariant_views = [InvariantView.from_invariant(invariant) for invariant in inputs.invariants]
    return ListInvariantsOperationResult(
        app_reference=inputs.app_reference,
        scope_label=inputs.scope_label,
        total=len(invariant_views),
        invariants=invariant_views,
    )


def run_replay_operation(
    root: Path | str,
    seed: str,
    *,
    mode: RunMode = RunMode.MCP,
) -> ReplayOperationResult:
    repo_root = Path(root)
    execution = _execute_replay(repo_root, seed)
    run = record_replay_run(
        repo_root,
        app_reference=execution.app_reference,
        source_run_id=execution.source_run_id,
        source_scope_label=execution.source_scope_label,
        seed=seed,
        summary=execution.explanation.to_dict(),
        mode=mode,
    )
    return ReplayOperationResult(
        run_id=run.run_id,
        source_run_id=execution.source_run_id,
        seed=seed,
        app_reference=execution.app_reference,
        explanation=execution.explanation,
    )


def run_explain_failure_operation(root: Path | str, seed: str) -> ExplainFailureOperationResult:
    repo_root = Path(root)
    execution = _execute_replay(repo_root, seed)
    return ExplainFailureOperationResult(
        seed=seed,
        source_run_id=execution.source_run_id,
        app_reference=execution.app_reference,
        explanation=execution.explanation,
    )


@dataclass(slots=True)
class _ReplayExecutionResult:
    source_run_id: str | None
    source_scope_label: str
    app_reference: str
    explanation: ReplayExplanation


def _execute_replay(root: Path, seed: str) -> _ReplayExecutionResult:
    source_run, record = replay_record_for_seed(root, seed)
    with patched_supported_boundaries(root):
        app = default_app_loader().load(record.app_reference, root)
        boundary_usage = _boundary_usage_for_loaded_app(record.app_reference, root)
        current_result = asyncio.run(
            run_asgi_app(
                app,
                method=record.method,
                path=record.path,
                json_body=record.request_payload,
                seed=record.seed_value,
                fault_plan=replay_fault_plan(record),
            )
        )
    current_response = ResponseExample(
        status_code=current_result.status_code,
        json=current_result.body if isinstance(current_result.body, dict) else None,
    )
    baseline_response = ResponseExample(
        status_code=record.baseline_status_code,
        json=record.baseline_body,
    )
    scenario = Scenario(
        method=record.method,
        path=record.path,
        request=RequestExample(method=record.method, path=record.path, json=record.request_payload),
        expected_response=baseline_response,
    )
    current_target_selection = replay_target_selection_artifact(
        app,
        record.app_reference,
        scenario,
        seed_value=record.seed_value,
        scenario_seed_start=_scenario_seed_start_for_record(source_run, record),
        root=root,
    )

    async def runner(_: Scenario) -> ResponseExample:
        return current_response

    replay_results = asyncio.run(run_differential_replay([scenario], runner))
    classification = replay_results[0].classification if replay_results else ReplayClassification.UNCHANGED
    diff = replay_results[0].diff if replay_results else {}
    current_trace = [*_unsupported_boundary_trace_events(boundary_usage), *current_result.trace]
    replay_transcript = normalize_execution_transcript(current_trace)
    replay_checkpoints = normalize_replay_checkpoints(
        current_trace,
        method=record.method,
        path=record.path,
    )
    replay_ledger = normalize_scheduler_ledger(
        seed=seed,
        method=record.method,
        path=record.path,
        trace=current_trace,
        target_selection=current_target_selection,
    )
    fidelity = compare_replay_contract(
        record.scheduler_ledger,
        replay_ledger,
        record.replay_checkpoints or record.execution_transcript,
        replay_checkpoints or replay_transcript,
        outcome_matches=_replay_outcome_matches_recorded_run(
            record.recorded_outcome,
            record.replay_checkpoints or record.execution_transcript,
            current_response.status_code,
            current_result.body,
        ),
    )
    explanation = explain_replay(
        seed=seed,
        method=record.method,
        path=record.path,
        baseline_status_code=record.baseline_status_code,
        baseline_body=record.baseline_body,
        current_status_code=current_response.status_code,
        current_body=current_result.body,
        classification=classification,
        diff=diff,
        trace=current_trace,
        fidelity=fidelity,
    )
    return _ReplayExecutionResult(
        source_run_id=source_run.run_id,
        source_scope_label=source_run.scope_label,
        app_reference=record.app_reference,
        explanation=explanation,
    )


def _resolve_scope(
    root: Path,
    *,
    target: Path | str | None,
    staged: bool,
    diff: str | None,
) -> VerifyScope:
    explicit_paths = None if target is None else [target]
    return resolve_verification_scope(
        root,
        explicit_paths=explicit_paths,
        staged=staged,
        diff=diff,
    )


def _replay_outcome_matches_recorded_run(
    recorded_outcome: ReplayResponseDetails | None,
    recorded_checkpoints: list | None,
    current_status_code: int | None,
    current_body,
) -> bool:
    if recorded_outcome is not None:
        return (
            recorded_outcome.status_code == current_status_code
            and recorded_outcome.body == current_body
        )

    if recorded_checkpoints is None:
        return True

    for checkpoint in reversed(recorded_checkpoints):
        if getattr(checkpoint, "kind", None) != "response_completed":
            continue
        return checkpoint.status_code == current_status_code
    return True


def _scenario_seed_start_for_record(source_run, record) -> int:
    matching_seed_values = sorted(
        candidate.seed_value
        for candidate in source_run.replay_traces
        if candidate.method == record.method
        and candidate.path == record.path
        and candidate.request_payload == record.request_payload
    )
    if not matching_seed_values:
        return record.seed_value
    return matching_seed_values[0]
