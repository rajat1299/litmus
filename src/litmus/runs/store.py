from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from uuid import uuid4

from litmus.errors import ReplayLookupError
from litmus.replay.trace import ReplayTraceRecord
from litmus.runs.models import (
    ActivityStatus,
    ActivityType,
    RunMode,
    RunStatus,
    VerificationActivity,
    VerificationRun,
)
from litmus.runs.summary import summarize_verification_result


def runs_root(root: Path | str) -> Path:
    return Path(root) / ".litmus" / "runs"


def latest_run_pointer_path(root: Path | str) -> Path:
    return runs_root(root) / "latest.json"


def latest_replayable_run_pointer_path(root: Path | str) -> Path:
    return runs_root(root) / "latest-replayable.json"


def run_directory(root: Path | str, run_id: str) -> Path:
    return runs_root(root) / run_id


def run_manifest_path(root: Path | str, run_id: str) -> Path:
    return run_directory(root, run_id) / "run.json"


def record_verification_run(
    root: Path | str,
    result,
    *,
    mode: RunMode,
    activity_type: ActivityType = ActivityType.VERIFY,
) -> VerificationRun:
    started_at = getattr(result, "started_at", None) or _timestamp()
    completed_at = getattr(result, "completed_at", None) or started_at
    run = VerificationRun(
        run_id=_run_id(),
        mode=mode,
        status=RunStatus.COMPLETED,
        repo_root=str(Path(root)),
        app_reference=result.app_reference,
        scope_label=result.scope_label,
        started_at=started_at,
        completed_at=completed_at,
        activities=[
            VerificationActivity(
                activity_id=_activity_id(activity_type),
                type=activity_type,
                status=ActivityStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                summary=summarize_verification_result(result),
            )
        ],
        replay_traces=list(result.replay_traces),
    )
    save_verification_run(root, run, replayable=True)
    return run


def record_replay_run(
    root: Path | str,
    *,
    app_reference: str,
    source_run_id: str | None,
    source_scope_label: str,
    seed: str,
    summary: dict[str, object],
    mode: RunMode = RunMode.LOCAL,
) -> VerificationRun:
    timestamp = _timestamp()
    run = VerificationRun(
        run_id=_run_id(),
        mode=mode,
        status=RunStatus.COMPLETED,
        repo_root=str(Path(root)),
        app_reference=app_reference,
        scope_label=source_scope_label,
        started_at=timestamp,
        completed_at=timestamp,
        activities=[
            VerificationActivity(
                activity_id=_activity_id(ActivityType.REPLAY),
                type=ActivityType.REPLAY,
                status=ActivityStatus.COMPLETED,
                started_at=timestamp,
                completed_at=timestamp,
                summary=summary,
                source_run_id=source_run_id,
                seed=seed,
            )
        ],
    )
    save_verification_run(root, run, replayable=False)
    return run


def record_invariant_review_run(
    root: Path | str,
    *,
    invariant_name: str,
    decision: str,
    reason: str | None,
    review_source: str,
    mode: RunMode = RunMode.LOCAL,
) -> VerificationRun:
    run = build_invariant_review_run(
        root,
        invariant_name=invariant_name,
        decision=decision,
        reason=reason,
        review_source=review_source,
        mode=mode,
    )
    persist_invariant_review_run(root, run)
    return run


def build_invariant_review_run(
    root: Path | str,
    *,
    invariant_name: str,
    decision: str,
    reason: str | None,
    review_source: str,
    mode: RunMode = RunMode.LOCAL,
) -> VerificationRun:
    timestamp = _timestamp()
    summary: dict[str, object] = {
        "invariant_name": invariant_name,
        "decision": decision,
        "review_source": review_source,
    }
    if reason is not None:
        summary["reason"] = reason
    return VerificationRun(
        run_id=_run_id(),
        mode=mode,
        status=RunStatus.COMPLETED,
        repo_root=str(Path(root)),
        app_reference=None,
        scope_label="curated invariant review",
        started_at=timestamp,
        completed_at=timestamp,
        activities=[
            VerificationActivity(
                activity_id=_activity_id(ActivityType.INVARIANT_REVIEW),
                type=ActivityType.INVARIANT_REVIEW,
                status=ActivityStatus.COMPLETED,
                started_at=timestamp,
                completed_at=timestamp,
                summary=summary,
            )
        ],
    )


def persist_invariant_review_run(root: Path | str, run: VerificationRun) -> None:
    save_verification_run(root, run, replayable=False, update_latest=False)


def discard_invariant_review_run(root: Path | str, run_id: str) -> None:
    manifest = run_manifest_path(root, run_id)
    manifest.unlink(missing_ok=True)
    run_dir = manifest.parent
    try:
        run_dir.rmdir()
    except OSError:
        return
    runs_dir = run_dir.parent
    try:
        runs_dir.rmdir()
    except OSError:
        return


def save_verification_run(
    root: Path | str,
    run: VerificationRun,
    *,
    replayable: bool,
    update_latest: bool = True,
) -> None:
    manifest_path = run_manifest_path(root, run.run_id)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if update_latest:
        _write_pointer(latest_run_pointer_path(root), run.run_id)
    if replayable and update_latest:
        _write_pointer(latest_replayable_run_pointer_path(root), run.run_id)


def load_verification_run(root: Path | str, run_id: str) -> VerificationRun:
    payload = json.loads(run_manifest_path(root, run_id).read_text(encoding="utf-8"))
    return VerificationRun.from_dict(payload)


def load_latest_verification_run(root: Path | str) -> VerificationRun:
    return load_verification_run(root, _read_pointer(latest_run_pointer_path(root)))


def load_latest_replayable_run(root: Path | str) -> VerificationRun:
    return load_verification_run(root, _read_pointer(latest_replayable_run_pointer_path(root)))


def replay_record_for_seed(root: Path | str, seed: str) -> tuple[VerificationRun, ReplayTraceRecord]:
    try:
        run = load_latest_replayable_run(root)
    except FileNotFoundError as exc:
        raise ReplayLookupError("No replay traces found. Run `litmus verify` first.") from exc
    for record in run.replay_traces:
        if record.seed == seed:
            return run, record
    raise ReplayLookupError(f"No replay trace found for {seed}.")


def clear_latest_replayable_run(root: Path | str) -> None:
    latest_replayable_run_pointer_path(root).unlink(missing_ok=True)


def _write_pointer(path: Path, run_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"run_id": run_id}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_pointer(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["run_id"]


def _run_id() -> str:
    return f"run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"


def _activity_id(activity_type: ActivityType) -> str:
    return f"{activity_type.value}-{uuid4().hex[:8]}"


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
