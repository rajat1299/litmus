from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from litmus.discovery.app import default_app_loader
from litmus.dst.asgi import run_asgi_app
from litmus.dst.engine import collect_verification_inputs, run_verification
from litmus.invariants.models import RequestExample, ResponseExample
from litmus.mcp.types import (
    ExplainFailureOperationResult,
    InvariantCounts,
    InvariantView,
    ListInvariantsOperationResult,
    PropertyCounts,
    ReplayCounts,
    ReplayOperationResult,
    VerifyOperationResult,
)
from litmus.replay.differential import ReplayClassification, run_differential_replay
from litmus.replay.explain import explain_replay
from litmus.replay.models import ReplayExplanation
from litmus.replay.trace import replay_fault_plan
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
    return VerifyOperationResult(
        run_id=run.run_id,
        app_reference=projection.app_reference,
        scope_label=projection.scope_label,
        routes=projection.routes,
        invariants=InvariantCounts(**projection.invariants),
        scenarios=projection.scenarios,
        replay=ReplayCounts(
            unchanged=projection.replay["unchanged"],
            breaking=projection.replay["breaking_change"],
            benign=projection.replay["benign_change"],
            improvement=projection.replay["improvement"],
        ),
        properties=PropertyCounts(**projection.properties),
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
    app = default_app_loader().load(record.app_reference, root)
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

    async def runner(_: Scenario) -> ResponseExample:
        return current_response

    replay_results = asyncio.run(run_differential_replay([scenario], runner))
    classification = replay_results[0].classification if replay_results else ReplayClassification.UNCHANGED
    diff = replay_results[0].diff if replay_results else {}
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
        trace=current_result.trace,
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
