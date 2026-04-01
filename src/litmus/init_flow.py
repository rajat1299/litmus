from __future__ import annotations

from pathlib import Path

from litmus.config import RepoConfig, load_repo_config, write_repo_config
from litmus.discovery.app import discover_app_reference
from litmus.init_models import InitBootstrapResult
from litmus.invariants.mined import mine_invariants_from_tests
from litmus.invariants.store import default_invariants_path, load_invariants, save_invariants


def bootstrap_repo(root: Path | str) -> InitBootstrapResult:
    repo_root = Path(root)
    config_path = repo_root / "litmus.yaml"
    invariants_path = default_invariants_path(repo_root)
    litmus_dir = invariants_path.parent

    config = load_repo_config(repo_root)
    app_reference = config.app or discover_app_reference(repo_root)

    if not config_path.exists():
        write_repo_config(config_path, RepoConfig(app=app_reference))
        config_status = "created"
    elif config.app:
        config_status = "existing"
    else:
        write_repo_config(config_path, RepoConfig(app=app_reference))
        config_status = "updated"

    litmus_directory_created = not litmus_dir.exists()
    litmus_dir.mkdir(parents=True, exist_ok=True)

    if invariants_path.exists():
        invariants_status = "existing"
        invariants = load_invariants(invariants_path)
    else:
        invariants = mine_invariants_from_tests(_iter_test_files(repo_root))
        save_invariants(invariants_path, invariants)
        invariants_status = "created"

    support_summary = _build_support_summary(config=config, invariant_count=len(invariants))

    return InitBootstrapResult(
        app_reference=app_reference,
        config_path=config_path,
        invariants_path=invariants_path,
        config_status=config_status,
        invariants_status=invariants_status,
        invariant_count=len(invariants),
        litmus_directory_created=litmus_directory_created,
        support_summary=support_summary,
    )


def _iter_test_files(root: Path) -> list[Path]:
    tests_root = root / "tests"
    if not tests_root.exists():
        return []

    return sorted(
        path
        for path in tests_root.rglob("*.py")
        if path.is_file() and (path.name.startswith("test_") or path.name.endswith("_test.py"))
    )


def _build_support_summary(config: RepoConfig, invariant_count: int) -> list[str]:
    summary = [
        "explicit app config detected" if config.app else "zero-config ASGI path detected",
    ]

    if invariant_count:
        suffix = "" if invariant_count == 1 else "s"
        summary.append(f"mined {invariant_count} invariant anchor{suffix}")
    else:
        summary.append("no mined test anchors detected yet")

    return summary
