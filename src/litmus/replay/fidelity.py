from __future__ import annotations

from litmus.dst.runtime import TraceEvent
from litmus.replay.models import ReplayCheckpoint, ReplayFidelityResult, ReplayFidelityStatus, replay_fidelity_not_checked


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
