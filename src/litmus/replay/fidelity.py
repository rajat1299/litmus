from __future__ import annotations

from litmus.dst.reachability import TargetSelectionArtifact
from litmus.dst.runtime import TraceEvent
from litmus.replay.models import (
    ReplayCheckpoint,
    ReplayDriftKind,
    ReplayFidelityResult,
    ReplayFidelityStatus,
    SchedulerDecision,
    replay_fidelity_not_checked,
)


def normalize_scheduler_ledger(
    *,
    seed: str,
    method: str,
    path: str,
    trace: list[TraceEvent],
    target_selection: TargetSelectionArtifact | None = None,
) -> list[SchedulerDecision]:
    ledger = [
        SchedulerDecision(kind="replay_seed", detail=seed),
        SchedulerDecision(kind="scenario", detail=f"{method.upper()} {path}"),
    ]
    if target_selection is not None:
        planned_fault_seed = target_selection.planned_fault_seed
        if planned_fault_seed.target != "none":
            ledger.append(
                SchedulerDecision(
                    kind="fault_target_selected",
                    target=planned_fault_seed.target,
                    detail=planned_fault_seed.selection_source,
                )
            )
        if planned_fault_seed.fault_kind != "none":
            ledger.append(
                SchedulerDecision(
                    kind="fault_kind_selected",
                    target=planned_fault_seed.target,
                    detail=planned_fault_seed.fault_kind,
                )
            )

    for event in trace:
        if event.kind == "fault_plan_selected":
            for scheduled_fault in event.metadata.get("schedule", []):
                ledger.append(
                    SchedulerDecision(
                        kind="fault_plan_selected",
                        step=int(scheduled_fault["step"]),
                        target=str(scheduled_fault["target"]),
                        detail=str(scheduled_fault["kind"]),
                        params=dict(scheduled_fault.get("params", {})),
                    )
                )
        elif event.kind == "fault_injected":
            ledger.append(
                SchedulerDecision(
                    kind="fault_injected",
                    step=event.metadata.get("step"),
                    target=str(event.metadata["target"]),
                    detail=str(event.metadata["fault_kind"]),
                    params=dict(event.metadata.get("params", {})),
                )
            )
    return ledger


def normalize_replay_checkpoints(
    trace: list[TraceEvent],
    *,
    method: str,
    path: str,
) -> list[ReplayCheckpoint]:
    checkpoints: list[ReplayCheckpoint] = []
    for event in trace:
        if event.kind == "request_started":
            checkpoints.append(ReplayCheckpoint(kind="request_started", detail=f"{method.upper()} {path}"))
        elif event.kind in {"boundary_detected", "boundary_intercepted"}:
            checkpoints.append(
                ReplayCheckpoint(
                    kind="boundary_enter",
                    target=str(event.metadata["boundary"]),
                )
            )
        elif event.kind == "boundary_simulated":
            checkpoints.append(
                ReplayCheckpoint(
                    kind="boundary_exit",
                    target=str(event.metadata["boundary"]),
                )
            )
        elif event.kind == "boundary_unsupported":
            checkpoints.append(
                ReplayCheckpoint(
                    kind="fault_bypassed",
                    target=str(event.metadata["boundary"]),
                    detail=str(event.metadata["detail"]),
                )
            )
        elif event.kind == "fault_injected":
            checkpoints.append(
                ReplayCheckpoint(
                    kind="fault_injected",
                    target=str(event.metadata["target"]),
                    detail=str(event.metadata["fault_kind"]),
                )
            )
        elif event.kind == "http_response_defaulted":
            checkpoints.append(
                ReplayCheckpoint(
                    kind="fault_defaulted",
                    target="http",
                    detail=f"{event.metadata['method']} {event.metadata['url']}",
                )
            )
        elif event.kind == "app_exception":
            checkpoints.append(
                ReplayCheckpoint(
                    kind="app_exception",
                    detail=f"{event.metadata['type']}: {event.metadata['message']}",
                )
            )
        elif event.kind == "response_started":
            checkpoints.append(
                ReplayCheckpoint(
                    kind="response_started",
                    status_code=int(event.metadata["status_code"]),
                )
            )
        elif event.kind == "request_completed":
            checkpoints.append(
                ReplayCheckpoint(
                    kind="response_completed",
                    status_code=int(event.metadata["status_code"]),
                )
            )
    return checkpoints


def normalize_execution_transcript(trace: list[TraceEvent]) -> list[ReplayCheckpoint]:
    transcript: list[ReplayCheckpoint] = []
    final_status_code: int | None = None

    for event in trace:
        if event.kind == "fault_plan_selected":
            for scheduled_fault in event.metadata.get("schedule", []):
                transcript.append(
                    ReplayCheckpoint(
                        kind="fault_plan_selected",
                        detail=(
                            f"{scheduled_fault['step']}:{scheduled_fault['target']}:"
                            f"{scheduled_fault['kind']}"
                        ),
                    )
                )
        elif event.kind == "boundary_intercepted":
            transcript.append(
                ReplayCheckpoint(
                    kind="boundary_intercepted",
                    target=str(event.metadata["boundary"]),
                    detail=str(event.metadata["supported_shape"]),
                )
            )
        elif event.kind == "boundary_simulated":
            transcript.append(
                ReplayCheckpoint(
                    kind="boundary_simulated",
                    target=str(event.metadata["boundary"]),
                )
            )
        elif event.kind == "fault_injected":
            transcript.append(
                ReplayCheckpoint(
                    kind="fault_injected",
                    target=str(event.metadata["target"]),
                    detail=str(event.metadata["fault_kind"]),
                )
            )
        elif event.kind == "http_response_defaulted":
            transcript.append(
                ReplayCheckpoint(
                    kind="default_response_used",
                    target="http",
                    detail=f"{event.metadata['method']} {event.metadata['url']}",
                )
            )
        elif event.kind == "app_exception":
            transcript.append(
                ReplayCheckpoint(
                    kind="app_exception",
                    detail=f"{event.metadata['type']}: {event.metadata['message']}",
                )
            )
        elif event.kind in {"request_completed", "response_started"}:
            status_code = event.metadata.get("status_code")
            if status_code is not None:
                final_status_code = int(status_code)

    if final_status_code is not None:
        transcript.append(ReplayCheckpoint(kind="response_completed", status_code=final_status_code))
    return transcript


def compare_execution_transcripts(
    recorded: list[ReplayCheckpoint] | None,
    replay: list[ReplayCheckpoint],
) -> ReplayFidelityResult:
    if recorded is None:
        return replay_fidelity_not_checked()

    max_len = max(len(recorded), len(replay))
    for index in range(max_len):
        recorded_checkpoint = recorded[index] if index < len(recorded) else None
        replay_checkpoint = replay[index] if index < len(replay) else None
        if recorded_checkpoint == replay_checkpoint:
            continue
        return ReplayFidelityResult(
            status=ReplayFidelityStatus.DRIFTED,
            recorded_step=index + 1,
            replay_step=index + 1,
            reason="Replay execution diverged from the recorded transcript.",
            recorded_checkpoint=recorded_checkpoint,
            replay_checkpoint=replay_checkpoint,
        )

    return ReplayFidelityResult(
        status=ReplayFidelityStatus.MATCHED,
        reason="Replay execution matched the recorded transcript.",
    )


def compare_replay_contract(
    recorded_decisions: list[SchedulerDecision] | None,
    replay_decisions: list[SchedulerDecision],
    recorded_checkpoints: list[ReplayCheckpoint] | None,
    replay_checkpoints: list[ReplayCheckpoint],
    *,
    outcome_matches: bool,
) -> ReplayFidelityResult:
    if recorded_decisions is None:
        return compare_execution_transcripts(recorded_checkpoints, replay_checkpoints)

    decision_result = _compare_scheduler_decisions(recorded_decisions, replay_decisions)
    if decision_result is not None:
        return decision_result

    checkpoint_result = _compare_replay_checkpoints(recorded_checkpoints, replay_checkpoints)
    if checkpoint_result is not None:
        return checkpoint_result

    if not outcome_matches:
        return ReplayFidelityResult(
            status=ReplayFidelityStatus.DRIFTED,
            drift_kind=ReplayDriftKind.OUTCOME_DRIFT,
            reason="Replay outcome drifted after scheduler decisions and checkpoints aligned.",
        )

    return ReplayFidelityResult(
        status=ReplayFidelityStatus.MATCHED,
        reason="Replay execution matched the recorded scheduler ledger and checkpoints.",
    )


def _compare_scheduler_decisions(
    recorded: list[SchedulerDecision],
    replay: list[SchedulerDecision],
) -> ReplayFidelityResult | None:
    max_len = max(len(recorded), len(replay))
    for index in range(max_len):
        recorded_decision = recorded[index] if index < len(recorded) else None
        replay_decision = replay[index] if index < len(replay) else None
        if recorded_decision == replay_decision:
            continue
        if recorded_decision is None:
            return ReplayFidelityResult(
                status=ReplayFidelityStatus.DRIFTED,
                drift_kind=ReplayDriftKind.UNEXPECTED_DECISION,
                recorded_step=index + 1,
                replay_step=index + 1,
                reason="Replay emitted an unexpected scheduler decision.",
                replay_decision=replay_decision,
            )
        if replay_decision is None:
            return ReplayFidelityResult(
                status=ReplayFidelityStatus.DRIFTED,
                drift_kind=ReplayDriftKind.DECISION_MISSING,
                recorded_step=index + 1,
                replay_step=index + 1,
                reason="Replay stopped before reproducing a recorded scheduler decision.",
                recorded_decision=recorded_decision,
            )
        return ReplayFidelityResult(
            status=ReplayFidelityStatus.DRIFTED,
            drift_kind=ReplayDriftKind.DECISION_MISMATCH,
            recorded_step=index + 1,
            replay_step=index + 1,
            reason="Replay decisions diverged from the recorded scheduler ledger.",
            recorded_decision=recorded_decision,
            replay_decision=replay_decision,
        )
    return None


def _compare_replay_checkpoints(
    recorded: list[ReplayCheckpoint] | None,
    replay: list[ReplayCheckpoint],
) -> ReplayFidelityResult | None:
    if recorded is None:
        return None

    max_len = max(len(recorded), len(replay))
    for index in range(max_len):
        recorded_checkpoint = recorded[index] if index < len(recorded) else None
        replay_checkpoint = replay[index] if index < len(replay) else None
        if recorded_checkpoint == replay_checkpoint:
            continue
        return ReplayFidelityResult(
            status=ReplayFidelityStatus.DRIFTED,
            drift_kind=ReplayDriftKind.CHECKPOINT_DRIFT,
            recorded_step=index + 1,
            replay_step=index + 1,
            reason="Replay checkpoints diverged after scheduler decisions stayed aligned.",
            recorded_checkpoint=recorded_checkpoint,
            replay_checkpoint=replay_checkpoint,
        )
    return None
