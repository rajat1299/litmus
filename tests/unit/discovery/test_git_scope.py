from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from litmus.discovery.git_scope import list_changed_files_for_diff, list_staged_files


def test_list_staged_files_invokes_git_cached_name_only(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, capture_output, text, check):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check
        return subprocess.CompletedProcess(command, 0, stdout="service/payments.py\ntests/test_payments.py\n")

    changed_files = list_staged_files(tmp_path, runner=fake_run)

    assert changed_files == ["service/payments.py", "tests/test_payments.py"]
    assert captured["command"] == ["git", "diff", "--cached", "--name-only"]
    assert captured["cwd"] == tmp_path
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["check"] is False


def test_list_changed_files_for_diff_invokes_git_name_only_with_range(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, capture_output, text, check):
        captured["command"] = command
        captured["cwd"] = cwd
        return subprocess.CompletedProcess(command, 0, stdout="service/refunds.py\n")

    changed_files = list_changed_files_for_diff(tmp_path, "origin/main...HEAD", runner=fake_run)

    assert changed_files == ["service/refunds.py"]
    assert captured["command"] == ["git", "diff", "--name-only", "origin/main...HEAD"]
    assert captured["cwd"] == tmp_path


def test_list_staged_files_raises_lookup_error_when_git_diff_fails(tmp_path: Path) -> None:
    def fake_run(command, *, cwd, capture_output, text, check):
        return subprocess.CompletedProcess(command, 128, stdout="", stderr="fatal: not a git repository")

    with pytest.raises(LookupError, match="Could not determine staged changes"):
        list_staged_files(tmp_path, runner=fake_run)
