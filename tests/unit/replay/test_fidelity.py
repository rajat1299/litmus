from __future__ import annotations

from litmus.dst.runtime import TraceEvent
from litmus.replay.fidelity import compare_execution_transcripts, normalize_execution_transcript
from litmus.replay.models import ReplayCheckpoint, ReplayFidelityStatus


def test_normalize_execution_transcript_keeps_stable_execution_checkpoints() -> None:
    transcript = normalize_execution_transcript(
        [
            TraceEvent(kind="request_started", metadata={"seed": 1}),
            TraceEvent(
                kind="fault_plan_selected",
                metadata={
                    "schedule": [
                        {"step": 1, "target": "redis", "kind": "timeout", "params": {}},
                    ]
                },
            ),
            TraceEvent(
                kind="boundary_intercepted",
                metadata={"boundary": "redis", "supported_shape": "redis.asyncio.from_url"},
            ),
            TraceEvent(kind="boundary_simulated", metadata={"boundary": "redis"}),
            TraceEvent(
                kind="fault_injected",
                metadata={
                    "step": 1,
                    "target": "redis",
                    "fault_kind": "timeout",
                    "operation": "get",
                    "key": "charge:ord-1",
                    "params": {},
                },
            ),
            TraceEvent(
                kind="http_response_defaulted",
                metadata={"step": 2, "method": "GET", "url": "https://service.invalid/fallback"},
            ),
            TraceEvent(kind="app_exception", metadata={"type": "RuntimeError", "message": "boom"}),
            TraceEvent(kind="request_completed", metadata={"status_code": 500}),
        ]
    )

    assert transcript == [
        ReplayCheckpoint(kind="fault_plan_selected", detail="1:redis:timeout"),
        ReplayCheckpoint(kind="boundary_intercepted", target="redis", detail="redis.asyncio.from_url"),
        ReplayCheckpoint(kind="boundary_simulated", target="redis"),
        ReplayCheckpoint(kind="fault_injected", target="redis", detail="timeout"),
        ReplayCheckpoint(kind="default_response_used", target="http", detail="GET https://service.invalid/fallback"),
        ReplayCheckpoint(kind="app_exception", detail="RuntimeError: boom"),
        ReplayCheckpoint(kind="response_completed", status_code=500),
    ]


def test_compare_execution_transcripts_reports_matched_when_transcripts_align() -> None:
    recorded = [
        ReplayCheckpoint(kind="fault_plan_selected", detail="1:http:timeout"),
        ReplayCheckpoint(kind="fault_injected", target="http", detail="timeout"),
        ReplayCheckpoint(kind="response_completed", status_code=200),
    ]

    result = compare_execution_transcripts(recorded, list(recorded))

    assert result.status is ReplayFidelityStatus.MATCHED
    assert result.recorded_step is None
    assert result.replay_step is None
    assert result.reason == "Replay execution matched the recorded transcript."
    assert result.recorded_checkpoint is None
    assert result.replay_checkpoint is None


def test_compare_execution_transcripts_reports_first_divergence() -> None:
    recorded = [
        ReplayCheckpoint(kind="fault_plan_selected", detail="1:redis:timeout"),
        ReplayCheckpoint(kind="fault_injected", target="redis", detail="timeout"),
        ReplayCheckpoint(kind="response_completed", status_code=500),
    ]
    replay = [
        ReplayCheckpoint(kind="fault_plan_selected", detail="1:redis:timeout"),
        ReplayCheckpoint(kind="boundary_detected", target="redis"),
        ReplayCheckpoint(kind="response_completed", status_code=500),
    ]

    result = compare_execution_transcripts(recorded, replay)

    assert result.status is ReplayFidelityStatus.DRIFTED
    assert result.recorded_step == 2
    assert result.replay_step == 2
    assert result.reason == "Replay execution diverged from the recorded transcript."
    assert result.recorded_checkpoint == ReplayCheckpoint(kind="fault_injected", target="redis", detail="timeout")
    assert result.replay_checkpoint == ReplayCheckpoint(kind="boundary_detected", target="redis")


def test_compare_execution_transcripts_reports_not_checked_for_legacy_artifacts() -> None:
    replay = [ReplayCheckpoint(kind="response_completed", status_code=200)]

    result = compare_execution_transcripts(None, replay)

    assert result.status is ReplayFidelityStatus.NOT_CHECKED
    assert result.reason == "Recorded replay artifact predates execution fidelity transcripts."
    assert result.recorded_checkpoint is None
    assert result.replay_checkpoint is None
