from __future__ import annotations


def parse_changed_files(diff_output: str) -> list[str]:
    if "diff --git " not in diff_output:
        return _parse_name_only_changed_files(diff_output)

    changed_files: list[str] = []

    for line in diff_output.splitlines():
        if not line.startswith("diff --git "):
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        new_path = parts[3]
        if not new_path.startswith("b/"):
            continue

        candidate = new_path[2:]
        if candidate not in changed_files:
            changed_files.append(candidate)

    return changed_files


def _parse_name_only_changed_files(diff_output: str) -> list[str]:
    changed_files: list[str] = []

    for line in diff_output.splitlines():
        candidate = line.strip()
        if not candidate or candidate in changed_files:
            continue
        changed_files.append(candidate)

    return changed_files
