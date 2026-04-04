from __future__ import annotations

from pathlib import Path
import sys
import textwrap

from litmus.mcp.tools import (
    run_explain_failure_operation,
    run_list_invariants_operation,
    run_replay_operation,
    run_verify_operation,
)
from litmus.replay.differential import ReplayClassification
from litmus.runs import RunMode, load_latest_verification_run


def test_run_verify_operation_records_mcp_run_and_returns_structured_summary(tmp_path: Path) -> None:
    repo_root = _build_verify_repo(tmp_path)

    result = run_verify_operation(repo_root)
    latest_run = load_latest_verification_run(repo_root)

    assert result.run_id == latest_run.run_id
    assert latest_run.mode.value == "mcp"
    assert result.app_reference == "service.app:app"
    assert result.scope_label == "full repo"
    assert result.invariants.total == 1
    assert result.invariants.confirmed == 1
    assert result.invariants.suggested == 0
    assert result.scenarios == 1
    assert result.replay.breaking == 0
    assert result.replay_seeds == ["seed:1"]


def test_run_verify_operation_passes_mode_through_to_run_verification(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class _DummyCounts:
        total = 0
        confirmed = 0
        suggested = 0

    class _DummyReplayCounts:
        unchanged = 0
        breaking = 0
        benign = 0
        improvement = 0

    class _DummyPropertyCounts:
        passed = 0
        failed = 0
        skipped = 0

    class _DummyResult:
        app_reference = "service.app:app"
        scope_label = "full repo"
        routes = []
        invariants = []
        scenarios = []
        replay_results = []
        replay_traces = []
        property_results = []

    monkeypatch.setattr(
        "litmus.mcp.tools._resolve_scope",
        lambda *_args, **_kwargs: captured.setdefault("scope", object()),
    )
    monkeypatch.setattr(
        "litmus.mcp.tools.run_verification",
        lambda root, *, mode, scope: captured.update({"root": root, "mode": mode, "scope": scope}) or _DummyResult(),
    )
    monkeypatch.setattr(
        "litmus.mcp.tools.record_verification_run",
        lambda *_args, **_kwargs: type("Run", (), {"run_id": "run-123"})(),
    )

    result = run_verify_operation(tmp_path, mode=RunMode.CI)

    assert result.run_id == "run-123"
    assert captured["mode"] is RunMode.CI


def test_run_list_invariants_operation_returns_visible_invariants(tmp_path: Path) -> None:
    repo_root = _build_verify_repo(tmp_path)

    result = run_list_invariants_operation(repo_root)

    assert result.app_reference == "service.app:app"
    assert result.scope_label == "full repo"
    assert result.total == 1
    assert [invariant.name for invariant in result.invariants] == ["health_returns_200"]
    assert result.invariants[0].status == "confirmed"
    assert result.invariants[0].method == "GET"
    assert result.invariants[0].path == "/health"


def test_run_replay_and_explain_failure_operations_return_structured_breaking_explanations(
    tmp_path: Path,
) -> None:
    repo_root = _build_breaking_verify_repo(tmp_path)

    verify_result = run_verify_operation(repo_root)
    assert verify_result.replay.breaking == 1

    replay_result = run_replay_operation(repo_root, "seed:1")
    explain_result = run_explain_failure_operation(repo_root, "seed:1")
    latest_run = load_latest_verification_run(repo_root)

    assert replay_result.run_id == latest_run.run_id
    assert latest_run.mode.value == "mcp"
    assert replay_result.explanation.classification is ReplayClassification.BREAKING_CHANGE
    assert replay_result.explanation.fidelity.status.value == "matched"
    assert replay_result.source_run_id is not None
    assert explain_result.source_run_id == replay_result.source_run_id
    assert explain_result.explanation.classification is ReplayClassification.BREAKING_CHANGE
    assert explain_result.explanation.fidelity.status.value == "matched"
    assert explain_result.explanation.next_step == replay_result.explanation.next_step
    assert replay_result.to_dict()["explanation"]["fidelity"]["status"] == "matched"


def test_run_verify_operation_observes_app_edits_across_repeated_calls(tmp_path: Path) -> None:
    repo_root = _build_verify_repo(tmp_path)

    first_result = run_verify_operation(repo_root)
    assert first_result.replay.breaking == 0
    assert first_result.replay.unchanged == 1

    _rewrite_health_app(
        repo_root / "service" / "app.py",
        status_code=500,
        status_value="broken",
    )

    second_result = run_verify_operation(repo_root)
    assert second_result.replay.breaking == 1
    assert second_result.replay.unchanged == 0


def _build_verify_repo(repo_root: Path) -> Path:
    _clear_service_modules()
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def get(self, path: str):
                    def decorator(func):
                        self.routes[("GET", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler()
                    await send(
                        {
                            "type": "http.response.start",
                            "status": response["status_code"],
                            "headers": [(b"content-type", b"application/json")],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": json.dumps(response["json"]).encode("utf-8"),
                        }
                    )


            app = FastAPI()


            @app.get("/health")
            async def health():
                return {"status_code": 200, "json": {"status": "ok"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tests_dir / "test_health.py").write_text(
        textwrap.dedent(
            """
            def test_health_returns_200():
                request = {
                    "method": "GET",
                    "path": "/health",
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "ok"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return repo_root


def _build_breaking_verify_repo(repo_root: Path) -> Path:
    repo_root = _build_verify_repo(repo_root)
    _rewrite_health_app(
        repo_root / "service" / "app.py",
        status_code=500,
        status_value="broken",
    )
    return repo_root


def _clear_service_modules() -> None:
    sys.modules.pop("service", None)
    sys.modules.pop("service.app", None)


def _rewrite_health_app(app_path: Path, *, status_code: int, status_value: str) -> None:
    app_path.write_text(
        app_path.read_text(encoding="utf-8")
        .replace(
            'return {"status_code": 200, "json": {"status": "ok"}}',
            f'return {{"status_code": {status_code}, "json": {{"status": "{status_value}"}}}}',
        )
        .replace(
            'return {"status_code": 500, "json": {"status": "broken"}}',
            f'return {{"status_code": {status_code}, "json": {{"status": "{status_value}"}}}}',
        ),
        encoding="utf-8",
    )
