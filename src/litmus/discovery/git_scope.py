from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Callable

from litmus.discovery.diff import parse_changed_files

GitRunner = Callable[..., subprocess.CompletedProcess[str]]


def list_staged_files(
    root: Path | str,
    *,
    runner: GitRunner = subprocess.run,
) -> list[str]:
    return _run_git_diff_name_only(
        root,
        ["git", "diff", "--cached", "--name-only"],
        error_message="Could not determine staged changes",
        runner=runner,
    )


def list_changed_files_for_diff(
    root: Path | str,
    diff_range: str,
    *,
    runner: GitRunner = subprocess.run,
) -> list[str]:
    return _run_git_diff_name_only(
        root,
        ["git", "diff", "--name-only", diff_range],
        error_message=f"Could not determine changed files for diff {diff_range}",
        runner=runner,
    )


def _run_git_diff_name_only(
    root: Path | str,
    command: list[str],
    *,
    error_message: str,
    runner: GitRunner,
) -> list[str]:
    result = runner(
        command,
        cwd=Path(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr:
            raise LookupError(f"{error_message}: {stderr}")
        raise LookupError(error_message)

    return parse_changed_files(result.stdout)
