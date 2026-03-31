from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TypeAlias

from watchfiles import watch

from litmus.dst.engine import VerificationResult, run_verification
from litmus.replay.trace import replay_trace_path, save_replay_trace_records
from litmus.reporting.console import render_verification_summary

WatchChange: TypeAlias = tuple[object, str]
WatchBatch: TypeAlias = Iterable[WatchChange]
Watcher: TypeAlias = Callable[[Path], Iterable[WatchBatch]]
Emitter: TypeAlias = Callable[[str], None]
Verifier: TypeAlias = Callable[[Path], VerificationResult]

IGNORED_PARTS = {
    ".git",
    ".litmus",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
}
RELEVANT_SUFFIXES = {".py", ".toml", ".yaml", ".yml"}
RELEVANT_FILES = {"litmus.yaml", "pyproject.toml"}


def run_watch(
    root: Path | str,
    *,
    watcher: Watcher | None = None,
    emit: Emitter = print,
    verify_runner: Verifier = run_verification,
) -> None:
    repo_root = Path(root)
    active_watcher = watch if watcher is None else watcher
    emit(f"Watching for changes in {repo_root}")

    for changes in active_watcher(repo_root):
        changed_paths = _relevant_paths(repo_root, changes)
        if not changed_paths:
            continue

        emit(f"Changed: {', '.join(changed_paths)}")
        try:
            result = verify_runner(repo_root)
        except Exception as exc:  # pragma: no cover - exercised via CLI path later
            replay_trace_path(repo_root).unlink(missing_ok=True)
            emit(f"Verification error: {exc}")
            continue

        save_replay_trace_records(repo_root, result.replay_traces)
        emit(render_verification_summary(result))


def _relevant_paths(root: Path, changes: WatchBatch) -> list[str]:
    relevant_paths: list[str] = []
    seen_paths: set[str] = set()

    for _change, raw_path in changes:
        changed_path = Path(raw_path)
        if not _is_relevant_path(root, changed_path):
            continue

        try:
            display_path = changed_path.relative_to(root).as_posix()
        except ValueError:
            display_path = changed_path.as_posix()

        if display_path in seen_paths:
            continue

        relevant_paths.append(display_path)
        seen_paths.add(display_path)

    return sorted(relevant_paths)


def _is_relevant_path(root: Path, changed_path: Path) -> bool:
    try:
        relative_path = changed_path.relative_to(root)
    except ValueError:
        relative_path = changed_path

    if any(part in IGNORED_PARTS for part in relative_path.parts):
        return False

    if relative_path.name in RELEVANT_FILES:
        return True

    return relative_path.suffix in RELEVANT_SUFFIXES
