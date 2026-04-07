from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from litmus.replay.trace import ReplayTraceRecord, replay_trace_record_from_dict, replay_trace_record_to_dict


class RunMode(str, Enum):
    LOCAL = "local"
    WATCH = "watch"
    CI = "ci"
    MCP = "mcp"


class RunStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class ActivityType(str, Enum):
    VERIFY = "verify"
    WATCH_ITERATION = "watch_iteration"
    REPLAY = "replay"
    PUBLISH_COMMENT = "publish_comment"
    INVARIANT_REVIEW = "invariant_review"


class ActivityStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class VerificationActivity:
    activity_id: str
    type: ActivityType
    status: ActivityStatus
    started_at: str
    completed_at: str
    summary: dict[str, Any] = field(default_factory=dict)
    source_run_id: str | None = None
    seed: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "activity_id": self.activity_id,
            "type": self.type.value,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": dict(self.summary),
        }
        if self.source_run_id is not None:
            payload["source_run_id"] = self.source_run_id
        if self.seed is not None:
            payload["seed"] = self.seed
        if self.error is not None:
            payload["error"] = self.error
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> VerificationActivity:
        return cls(
            activity_id=payload["activity_id"],
            type=ActivityType(payload["type"]),
            status=ActivityStatus(payload["status"]),
            started_at=payload["started_at"],
            completed_at=payload["completed_at"],
            summary=dict(payload.get("summary", {})),
            source_run_id=payload.get("source_run_id"),
            seed=payload.get("seed"),
            error=payload.get("error"),
        )


@dataclass(slots=True)
class VerificationRun:
    run_id: str
    mode: RunMode
    status: RunStatus
    repo_root: str
    app_reference: str | None
    scope_label: str
    started_at: str
    completed_at: str
    activities: list[VerificationActivity] = field(default_factory=list)
    replay_traces: list[ReplayTraceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode.value,
            "status": self.status.value,
            "repo_root": self.repo_root,
            "app_reference": self.app_reference,
            "scope_label": self.scope_label,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "activities": [activity.to_dict() for activity in self.activities],
            "artifacts": {
                "replay_traces": [
                    replay_trace_record_to_dict(record)
                    for record in self.replay_traces
                ],
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> VerificationRun:
        artifacts = payload.get("artifacts", {})
        return cls(
            run_id=payload["run_id"],
            mode=RunMode(payload["mode"]),
            status=RunStatus(payload["status"]),
            repo_root=payload["repo_root"],
            app_reference=payload.get("app_reference"),
            scope_label=payload.get("scope_label", "full repo"),
            started_at=payload["started_at"],
            completed_at=payload["completed_at"],
            activities=[
                VerificationActivity.from_dict(activity_payload)
                for activity_payload in payload.get("activities", [])
            ],
            replay_traces=[
                replay_trace_record_from_dict(record_payload)
                for record_payload in artifacts.get("replay_traces", [])
            ],
        )
