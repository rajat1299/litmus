from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import textwrap


def test_litmus_verify_runs_end_to_end_against_mined_scenarios(tmp_path) -> None:
    repo_root = tmp_path
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

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
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


            @app.post("/payments/charge")
            async def charge(payload):
                amount = payload["amount"]
                if amount > 500:
                    return {"status_code": 402, "json": {"status": "declined"}}
                return {"status_code": 200, "json": {"status": "charged"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200_on_success():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"amount": 100},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200


            def test_charge_returns_402_on_decline():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"amount": 1000},
                }
                response = {
                    "status_code": 402,
                    "json": {"status": "declined"},
                }

                assert response["status_code"] == 402
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Litmus verify" in result.stdout
    assert "App: service.app:app" in result.stdout
    assert _latest_verify_summary(repo_root) == {
        "routes": 1,
        "invariants": {
            "total": 2,
            "confirmed": 2,
            "suggested": 0,
        },
        "scenarios": 2,
        "replay": {
            "unchanged": 2,
            "breaking_change": 0,
            "benign_change": 0,
            "improvement": 0,
        },
        "properties": {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        },
        "compatibility": _expected_not_detected_compatibility(),
        "confidence": 1.0,
    }


def test_litmus_verify_under_reports_confidence_when_no_signals_exist(tmp_path) -> None:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    service_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def get(self, path: str):
                    def decorator(func):
                        self.routes[("GET", path)] = func
                        return func

                    return decorator


            app = FastAPI()


            @app.get("/health")
            async def health():
                return {"status": "ok"}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Litmus verify" in result.stdout
    assert _latest_verify_summary(repo_root) == {
        "routes": 1,
        "invariants": {
            "total": 0,
            "confirmed": 0,
            "suggested": 0,
        },
        "scenarios": 0,
        "replay": {
            "unchanged": 0,
            "breaking_change": 0,
            "benign_change": 0,
            "improvement": 0,
        },
        "properties": {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        },
        "compatibility": _expected_not_detected_compatibility(),
        "confidence": 0.0,
    }


def test_litmus_verify_reports_app_load_error_cleanly(tmp_path: Path) -> None:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    service_dir.mkdir()

    (repo_root / "litmus.yaml").write_text('app: "service.app:missing_app"\n', encoding="utf-8")
    (service_dir / "app.py").write_text("app = object()\n", encoding="utf-8")

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 1
    assert "Could not load ASGI app 'service.app:missing_app'" in result.stderr
    assert "Traceback" not in result.stderr


def test_litmus_verify_reports_scope_error_cleanly(tmp_path: Path) -> None:
    result = subprocess.run(
        ["litmus", "verify", "missing.py"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    assert "Path does not exist: missing.py" in result.stderr
    assert "Traceback" not in result.stderr


def test_litmus_verify_exercises_cross_layer_dst_with_zero_config_interception(tmp_path: Path) -> None:
    repo_root = _write_cross_layer_dst_repo(tmp_path)

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 1, result.stdout
    assert "DST coverage:" in result.stdout
    assert "- sqlalchemy: detected, intercepted, simulated, faulted" in result.stdout
    assert "- redis: detected, intercepted, simulated, faulted" in result.stdout

    latest_run_id = json.loads((repo_root / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))
    replay_traces = run_payload["artifacts"]["replay_traces"]
    assert replay_traces
    assert any(
        any(event["kind"] == "fault_injected" and event["metadata"]["target"] == "sqlalchemy" for event in trace["trace"])
        for trace in replay_traces
    )
    assert any(
        any(event["kind"] == "fault_injected" and event["metadata"]["target"] == "redis" for event in trace["trace"])
        for trace in replay_traces
    )


def test_litmus_verify_supports_redis_from_url_class_constructor(tmp_path: Path) -> None:
    repo_root = _write_cross_layer_dst_repo(tmp_path, redis_constructor_shape="class_from_url")

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 1, result.stdout
    assert "DST coverage:" in result.stdout
    assert "- redis: detected, intercepted, simulated, faulted" in result.stdout
    assert "Traceback" not in result.stderr


def test_litmus_verify_does_not_schedule_redis_for_unused_supported_helper(tmp_path: Path) -> None:
    repo_root = _write_http_only_repo_with_unused_redis_helper(tmp_path)

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 1, result.stdout

    latest_run_id = json.loads((repo_root / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))
    replay_traces = run_payload["artifacts"]["replay_traces"]
    assert replay_traces
    assert all(
        all(item["target"] == "http" for item in event["metadata"]["schedule"])
        for trace in replay_traces
        for event in trace["trace"]
        if event["kind"] == "fault_plan_selected"
    )
    assert not any(
        any(event["kind"] == "fault_injected" and event["metadata"]["target"] == "redis" for event in trace["trace"])
        for trace in replay_traces
    )


def test_litmus_verify_schedules_fault_only_reachable_redis_in_local_seed_budget(tmp_path: Path) -> None:
    repo_root = _write_fault_path_reachability_repo(tmp_path)

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stdout

    latest_run_id = json.loads((repo_root / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))
    replay_traces = run_payload["artifacts"]["replay_traces"]
    planned_targets = [
        event["metadata"]["schedule"][0]["target"]
        for trace in replay_traces
        for event in trace["trace"]
        if event["kind"] == "fault_plan_selected" and event["metadata"]["schedule"]
    ]

    assert planned_targets[:2] == ["http", "redis"]
    assert planned_targets.count("redis") >= 1
    assert replay_traces[0]["target_selection"] == {
        "clean_path_targets": ["http"],
        "fault_path_targets": ["redis"],
        "selected_targets": ["http", "redis"],
        "probe_records": [
            {
                "phase": "clean_path",
                "trigger_target": None,
                "trigger_fault_kind": None,
                "discovered_targets": ["http"],
            },
            {
                "phase": "fault_path",
                "trigger_target": "http",
                "trigger_fault_kind": "timeout",
                "discovered_targets": ["http", "redis"],
            },
            {
                "phase": "fault_path",
                "trigger_target": "redis",
                "trigger_fault_kind": "timeout",
                "discovered_targets": ["http"],
            },
        ],
        "planned_fault_seed": {
            "seed_value": 1,
            "target": "http",
            "fault_kind": "timeout",
            "selection_source": "clean_path",
        },
    }
    assert replay_traces[1]["target_selection"]["planned_fault_seed"] == {
        "seed_value": 2,
        "target": "redis",
        "fault_kind": "timeout",
        "selection_source": "fault_path",
    }


def test_litmus_verify_reports_partial_dst_coverage_for_unsupported_redis_constructor(tmp_path: Path) -> None:
    repo_root = _write_unsupported_redis_repo(tmp_path)

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "DST coverage:" in result.stdout
    assert "- redis: unsupported, detected" in result.stdout
    assert "Compatibility:" in result.stdout
    assert "- redis: unsupported (Unsupported constructor or type import in loaded app modules.)" in result.stdout

    latest_run_id = json.loads((repo_root / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))
    compatibility = run_payload["activities"][0]["summary"]["compatibility"]
    assert compatibility["matrix"]["python"] == "3.11+"
    assert compatibility["boundaries"]["redis"]["status"] == "unsupported"
    assert compatibility["boundaries"]["redis"]["unsupported_details"] == [
        "Unsupported constructor or type import in loaded app modules."
    ]


def test_litmus_verify_reports_suggested_route_gaps_separately_from_confirmed_coverage(tmp_path: Path) -> None:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (repo_root / "litmus.yaml").write_text(
        textwrap.dedent(
            """
            app: service.app:app
            suggested_invariants: true
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "payments.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations


            async def charge_payment(payload):
                return {"status_code": 200, "json": {"status": "charged"}}


            async def refund_payment(payload):
                return {"status_code": 200, "json": {"status": "refunded"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json

            from service.payments import charge_payment, refund_payment


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
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


            @app.post("/payments/charge")
            async def charge(payload):
                return await charge_payment(payload)


            @app.post("/payments/refund")
            async def refund(payload):
                return await refund_payment(payload)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"amount": 100},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = _latest_verify_summary(repo_root)
    assert summary["invariants"] == {"total": 2, "confirmed": 1, "suggested": 1}
    assert summary["scenarios"] == 1
    assert (
        "refund_post_payments_refund_needs_confirmed_anchor: "
        "POST /payments/refund is selected for verification without a confirmed mined invariant anchor."
    ) in result.stdout


def test_litmus_verify_surfaces_curated_suggested_invariants_without_duplicate_generated_route_gaps(
    tmp_path: Path,
) -> None:
    repo_root = _build_curated_suggestions_repo(tmp_path)

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = _latest_verify_summary(repo_root)
    assert summary["invariants"] == {"total": 2, "confirmed": 1, "suggested": 1}
    assert summary["scenarios"] == 1
    assert "refund_needs_review: Review refund behavior before trusting this endpoint." in result.stdout
    assert "charge_returns_200_from_store" not in result.stdout
    assert "refund_post_payments_refund_needs_confirmed_anchor" not in result.stdout


def test_litmus_verify_scopes_to_curated_suggestions_file(tmp_path: Path) -> None:
    repo_root = _build_curated_suggestions_repo(tmp_path)

    result = subprocess.run(
        ["litmus", "verify", ".litmus/invariants.yaml"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Scope: paths: .litmus/invariants.yaml" in result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["routes"] == 1
    assert summary["invariants"] == {"total": 1, "confirmed": 0, "suggested": 1}
    assert summary["scenarios"] == 0
    assert "refund_needs_review: Review refund behavior before trusting this endpoint." in result.stdout


def test_litmus_verify_scopes_to_staged_curated_suggestions_file(tmp_path: Path) -> None:
    repo_root = _build_curated_suggestions_repo(tmp_path)
    _init_git_repo(repo_root)

    suggestions_file = repo_root / ".litmus" / "invariants.yaml"
    suggestions_file.write_text(
        suggestions_file.read_text(encoding="utf-8").replace(
            "Review refund behavior before trusting this endpoint.",
            "Review refund behavior before trusting this route.",
        ),
        encoding="utf-8",
    )
    _git(repo_root, "add", ".litmus/invariants.yaml")

    result = subprocess.run(
        ["litmus", "verify", "--staged"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Scope: staged diff" in result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["routes"] == 1
    assert summary["invariants"] == {"total": 1, "confirmed": 0, "suggested": 1}
    assert summary["scenarios"] == 0
    assert "refund_needs_review: Review refund behavior before trusting this route." in result.stdout


def test_litmus_verify_scopes_to_explicit_changed_path(tmp_path: Path) -> None:
    repo_root = _build_scoped_verify_repo(tmp_path)

    result = subprocess.run(
        ["litmus", "verify", "service/refunds.py"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Scope: paths: service/refunds.py" in result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["routes"] == 1
    assert summary["invariants"]["total"] == 1
    assert summary["scenarios"] == 1
    assert summary["replay"]["unchanged"] == 1


def test_litmus_verify_scopes_to_explicit_changed_test_file(tmp_path: Path) -> None:
    repo_root = _build_scoped_verify_repo(tmp_path)

    result = subprocess.run(
        ["litmus", "verify", "tests/test_payments.py"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Scope: paths: tests/test_payments.py" in result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["routes"] == 2
    assert summary["invariants"]["total"] == 2
    assert summary["scenarios"] == 2


def test_litmus_verify_scopes_to_staged_changes(tmp_path: Path) -> None:
    repo_root = _build_scoped_verify_repo(tmp_path)
    _init_git_repo(repo_root)

    refunds_file = repo_root / "service" / "refunds.py"
    refunds_file.write_text(
        refunds_file.read_text(encoding="utf-8").replace('"status_code": 200', '"status_code": 500'),
        encoding="utf-8",
    )
    _git(repo_root, "add", "service/refunds.py")

    result = subprocess.run(
        ["litmus", "verify", "--staged"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 1, result.stderr
    assert "Scope: staged diff" in result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["routes"] == 1
    assert summary["invariants"]["total"] == 1
    assert summary["scenarios"] == 1


def test_litmus_verify_scopes_to_staged_test_file_changes(tmp_path: Path) -> None:
    repo_root = _build_scoped_verify_repo(tmp_path)
    _init_git_repo(repo_root)

    payments_test_file = repo_root / "tests" / "test_payments.py"
    payments_test_file.write_text(
        payments_test_file.read_text(encoding="utf-8").replace("charged", "charged-now"),
        encoding="utf-8",
    )
    _git(repo_root, "add", "tests/test_payments.py")

    result = subprocess.run(
        ["litmus", "verify", "--staged"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Scope: staged diff" in result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["routes"] == 2
    assert summary["invariants"]["total"] == 2
    assert summary["scenarios"] == 2


def test_litmus_verify_scopes_to_named_diff_range(tmp_path: Path) -> None:
    repo_root = _build_scoped_verify_repo(tmp_path)
    _init_git_repo(repo_root)

    refunds_file = repo_root / "service" / "refunds.py"
    refunds_file.write_text(
        refunds_file.read_text(encoding="utf-8").replace('"status_code": 200', '"status_code": 500'),
        encoding="utf-8",
    )
    _git(repo_root, "add", "service/refunds.py")
    _git(repo_root, "commit", "-m", "change refund behavior")

    result = subprocess.run(
        ["litmus", "verify", "--diff", "HEAD~1...HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 1, result.stderr
    assert "Scope: diff HEAD~1...HEAD" in result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["routes"] == 1
    assert summary["invariants"]["total"] == 1
    assert summary["scenarios"] == 1


def test_litmus_verify_runs_faulted_http_dst_replay_in_main_path(tmp_path: Path) -> None:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import httpx
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
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get("https://service.invalid/orders/123")
                    except httpx.HTTPError:
                        return {"status_code": 503, "json": {"status": "upstream_unavailable"}}

                if response.status_code >= 500:
                    return {"status_code": 503, "json": {"status": "upstream_unavailable"}}

                return {"status_code": 200, "json": {"status": "ok"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_health.py").write_text(
        textwrap.dedent(
            """
            def test_health_returns_200_when_upstream_is_healthy():
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

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 1, result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["scenarios"] == 1
    assert summary["replay"] == {
        "unchanged": 0,
        "breaking_change": 3,
        "benign_change": 0,
        "improvement": 0,
    }


def test_litmus_verify_reports_breaking_seed_when_fault_exception_escapes_app(tmp_path: Path) -> None:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import httpx
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
                async with httpx.AsyncClient() as client:
                    response = await client.get("https://service.invalid/orders/123")

                return {"status_code": response.status_code, "json": {"status": "ok"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_health.py").write_text(
        textwrap.dedent(
            """
            def test_health_returns_200_when_upstream_is_healthy():
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

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 1
    assert "Litmus verify" in result.stdout
    summary = _latest_verify_summary(repo_root)
    assert summary["scenarios"] == 1
    assert summary["replay"]["breaking_change"] == 3
    assert "Traceback" not in result.stderr


def test_litmus_verify_keeps_unknown_followup_json_request_parseable_after_caught_fault(tmp_path: Path) -> None:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import httpx
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
                async with httpx.AsyncClient() as client:
                    try:
                        await client.get("https://service.invalid/orders/primary")
                    except httpx.HTTPError:
                        pass

                    metadata = (await client.get("https://service.invalid/orders/secondary")).json()

                return {"status_code": 200, "json": {"status": "ok", "metadata": metadata}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_health.py").write_text(
        textwrap.dedent(
            """
            def test_health_returns_200_when_upstream_health_can_be_checked():
                request = {
                    "method": "GET",
                    "path": "/health",
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "ok", "metadata": {}},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = _latest_verify_summary(repo_root)
    assert summary["scenarios"] == 1
    assert summary["replay"]["unchanged"] == 3


def _build_scoped_verify_repo(repo_root: Path) -> Path:
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "payments.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations


            async def charge_payment(payload):
                return {"status_code": 200, "json": {"status": "charged"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (service_dir / "refunds.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations


            async def refund_payment(payload):
                return {"status_code": 200, "json": {"status": "refunded"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json

            from service.payments import charge_payment
            from service.refunds import refund_payment


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
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


            @app.post("/payments/charge")
            async def charge(payload):
                return await charge_payment(payload)


            @app.post("/payments/refund")
            async def refund(payload):
                return await refund_payment(payload)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"amount": 100},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200


            def test_refund_returns_200():
                request = {
                    "method": "POST",
                    "path": "/payments/refund",
                    "json": {"payment_id": "pay_123"},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "refunded"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return repo_root


def _build_curated_suggestions_repo(repo_root: Path) -> Path:
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    litmus_dir = repo_root / ".litmus"
    service_dir.mkdir()
    tests_dir.mkdir()
    litmus_dir.mkdir()

    (repo_root / "litmus.yaml").write_text(
        textwrap.dedent(
            """
            app: service.app:app
            suggested_invariants: true
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (litmus_dir / "invariants.yaml").write_text(
        textwrap.dedent(
            """
            - name: charge_returns_200_from_store
              source: manual:confirmed
              status: confirmed
              type: differential
              request:
                method: POST
                path: /payments/charge
              response:
                status_code: 200
            - name: refund_needs_review
              source: manual:suggested
              status: suggested
              type: differential
              request:
                method: POST
                path: /payments/refund
              reasoning: Review refund behavior before trusting this endpoint.
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "payments.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations


            async def charge_payment(payload):
                return {"status_code": 200, "json": {"status": "charged"}}


            async def refund_payment(payload):
                return {"status_code": 200, "json": {"status": "refunded"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json

            from service.payments import charge_payment, refund_payment


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
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


            @app.post("/payments/charge")
            async def charge(payload):
                return await charge_payment(payload)


            @app.post("/payments/refund")
            async def refund(payload):
                return await refund_payment(payload)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"amount": 100},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return repo_root


def _init_git_repo(repo_root: Path) -> None:
    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "litmus@example.com")
    _git(repo_root, "config", "user.name", "Litmus Tests")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "initial")


def _git(repo_root: Path, *args: str) -> None:
    env = dict(os.environ)
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        }
    )
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr


def _write_cross_layer_dst_repo(tmp_path: Path, *, redis_constructor_shape: str = "module_from_url") -> Path:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    redis_dir = repo_root / "redis"
    sqlalchemy_dir = repo_root / "sqlalchemy"
    sqlalchemy_ext_dir = sqlalchemy_dir / "ext"
    service_dir.mkdir()
    tests_dir.mkdir()
    redis_dir.mkdir()
    sqlalchemy_dir.mkdir()
    sqlalchemy_ext_dir.mkdir()

    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        textwrap.dedent(
            """
            class Redis:
                def __init__(self, *args, **kwargs):
                    raise RuntimeError("litmus should patch redis.asyncio.Redis")


            def from_url(*args, **kwargs):
                raise RuntimeError("litmus should patch redis.asyncio.from_url")


            class RedisCluster:
                def __init__(self, *args, **kwargs):
                    self._store = {}

                async def get(self, key):
                    return self._store.get(key)

                async def set(self, key, value):
                    self._store[key] = value
                    return True
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (sqlalchemy_dir / "__init__.py").write_text(
        textwrap.dedent(
            """
            from types import SimpleNamespace


            class String:
                pass


            class MetaData:
                pass


            class Condition:
                def __init__(self, column_name, value):
                    self.column_name = column_name
                    self.value = value


            class Column:
                def __init__(self, name, type_=None, primary_key=False):
                    self.name = name
                    self.type_ = type_
                    self.primary_key = primary_key

                def __eq__(self, value):
                    return Condition(self.name, value)


            class _PrimaryKey:
                def __init__(self, columns):
                    self.columns = tuple(column for column in columns if column.primary_key)


            class Table:
                def __init__(self, name, metadata, *columns):
                    self.name = name
                    self.metadata = metadata
                    self.columns = tuple(columns)
                    self.primary_key = _PrimaryKey(columns)
                    self.c = SimpleNamespace(**{column.name: column for column in columns})


            class Insert:
                __litmus_statement_type__ = "insert"

                def __init__(self, table):
                    self.table = table
                    self.values_dict = {}

                def values(self, **kwargs):
                    self.values_dict.update(kwargs)
                    return self


            class Select:
                __litmus_statement_type__ = "select"

                def __init__(self, table):
                    self.table = table
                    self.filter = None

                def where(self, condition):
                    self.filter = condition
                    return self


            def insert(table):
                return Insert(table)


            def select(table):
                return Select(table)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (sqlalchemy_ext_dir / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext_dir / "asyncio.py").write_text(
        textwrap.dedent(
            """
            class AsyncSession:
                def __init__(self, *args, **kwargs):
                    self.args = args
                    self.kwargs = kwargs


            def create_async_engine(*args, **kwargs):
                raise RuntimeError("litmus should patch sqlalchemy.ext.asyncio.create_async_engine")


            def async_sessionmaker(*args, **kwargs):
                raise RuntimeError("litmus should patch sqlalchemy.ext.asyncio.async_sessionmaker")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    redis_import = "from redis.asyncio import from_url"
    redis_constructor = 'redis = from_url("redis://cache")'
    if redis_constructor_shape == "class_from_url":
        redis_import = "from redis.asyncio import Redis"
        redis_constructor = 'redis = Redis.from_url("redis://cache")'

    app_source = textwrap.dedent(
        """
            from __future__ import annotations

            import json

            import httpx
            __REDIS_IMPORT__
            from sqlalchemy import Column, MetaData, String, Table, insert, select
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
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
            metadata = MetaData()
            ledger = Table(
                "ledger",
                metadata,
                Column("id", String, primary_key=True),
                Column("status", String),
            )
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
            __REDIS_CONSTRUCTOR__


            @app.post("/payments/charge")
            async def charge(payload):
                payment_id = payload["payment_id"]

                async with httpx.AsyncClient() as client:
                    await client.get("https://processor.invalid/charge")

                cached = await redis.get(f"charge:{payment_id}")
                if cached == "charged":
                    return {"status_code": 200, "json": {"status": "charged", "source": "cache"}}

                async with SessionLocal() as session:
                    await session.begin()
                    existing = await session.execute(
                        select(ledger).where(ledger.c.id == payment_id)
                    )
                    if existing.scalar_one_or_none() is None:
                        await session.execute(
                            insert(ledger).values(id=payment_id, status="charged")
                        )
                    await session.commit()

                await redis.set(f"charge:{payment_id}", "charged")
                return {"status_code": 200, "json": {"status": "charged"}}
            """
    ).strip()
    app_source = app_source.replace("__REDIS_IMPORT__", redis_import)
    app_source = app_source.replace("__REDIS_CONSTRUCTOR__", redis_constructor)

    (service_dir / "app.py").write_text(
        app_source
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"payment_id": "ord-1"},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return repo_root


def _write_fault_path_reachability_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    redis_dir = repo_root / "redis"
    service_dir.mkdir()
    tests_dir.mkdir()
    redis_dir.mkdir()

    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        textwrap.dedent(
            """
            class Redis:
                def __init__(self):
                    self._store = {}

                @classmethod
                def from_url(cls, *args, **kwargs):
                    raise RuntimeError("litmus should patch redis.asyncio.Redis.from_url")

                async def get(self, key):
                    return self._store.get(key)

                async def set(self, key, value):
                    self._store[key] = value
                    return True


            def from_url(*args, **kwargs):
                raise RuntimeError("litmus should patch redis.asyncio.from_url")


            class RedisCluster:
                pass
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json

            import httpx
            from redis.asyncio import from_url


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
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
            redis = from_url("redis://cache")


            @app.post("/payments/charge")
            async def charge(payload):
                payment_id = payload["payment_id"]
                try:
                    async with httpx.AsyncClient() as client:
                        await client.get("https://processor.invalid/charge")
                except httpx.HTTPError:
                    try:
                        cached = await redis.get(f"charge:{payment_id}")
                        if cached is None:
                            await redis.set(f"charge:{payment_id}", "charged")
                    except Exception:
                        return {"status_code": 503, "json": {"status": "retry_later"}}
                    return {"status_code": 200, "json": {"status": "charged", "source": "fallback"}}

                return {"status_code": 200, "json": {"status": "charged", "source": "primary"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"payment_id": "ord-1"},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged", "source": "primary"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return repo_root


def _write_http_only_repo_with_unused_redis_helper(tmp_path: Path) -> Path:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    redis_dir = repo_root / "redis"
    service_dir.mkdir()
    tests_dir.mkdir()
    redis_dir.mkdir()

    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        textwrap.dedent(
            """
            class Redis:
                @classmethod
                def from_url(cls, *args, **kwargs):
                    raise RuntimeError("litmus should patch redis.asyncio.Redis.from_url")


            def from_url(*args, **kwargs):
                raise RuntimeError("litmus should patch redis.asyncio.from_url")


            class RedisCluster:
                pass
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json

            import httpx
            import redis.asyncio as redis


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
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


            def build_unused_cache_client():
                return redis.Redis.from_url("redis://cache")


            app = FastAPI()


            @app.post("/payments/charge")
            async def charge(payload):
                async with httpx.AsyncClient() as client:
                    await client.get("https://processor.invalid/charge")
                return {"status_code": 200, "json": {"status": "charged"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"payment_id": "ord-1"},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return repo_root


def _write_unsupported_redis_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    redis_dir = repo_root / "redis"
    service_dir.mkdir()
    tests_dir.mkdir()
    redis_dir.mkdir()

    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        textwrap.dedent(
            """
            class Redis:
                def __init__(self, *args, **kwargs):
                    raise RuntimeError("litmus should patch redis.asyncio.Redis")


            def from_url(*args, **kwargs):
                raise RuntimeError("litmus should patch redis.asyncio.from_url")


            class RedisCluster:
                def __init__(self, *args, **kwargs):
                    self._store = {}

                async def get(self, key):
                    return self._store.get(key)

                async def set(self, key, value):
                    self._store[key] = value
                    return True
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json

            from redis.asyncio import RedisCluster


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    request = await receive()
                    payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler(payload)
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
            redis = RedisCluster()


            @app.post("/payments/charge")
            async def charge(payload):
                payment_id = payload["payment_id"]
                cached = await redis.get(f"charge:{payment_id}")
                if cached is None:
                    await redis.set(f"charge:{payment_id}", "charged")
                return {"status_code": 200, "json": {"status": "charged"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"payment_id": "ord-2"},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return repo_root


def _latest_verify_summary(repo_root: Path) -> dict:
    latest_run_id = json.loads((repo_root / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))
    return run_payload["activities"][0]["summary"]


def _expected_not_detected_compatibility() -> dict[str, object]:
    return {
        "matrix": {
            "python": "3.11+",
            "asgi": "FastAPI / Starlette-style ASGI apps",
            "http": {
                "package": "httpx/aiohttp",
                "supported_shapes": ["httpx/aiohttp"],
            },
            "sqlalchemy": {
                "package": "sqlalchemy.ext.asyncio",
                "supported_shapes": [
                    "sqlalchemy.ext.asyncio.create_async_engine",
                    "sqlalchemy.ext.asyncio.async_sessionmaker",
                ],
            },
            "redis": {
                "package": "redis.asyncio",
                "supported_shapes": [
                    "redis.asyncio.Redis",
                    "redis.asyncio.Redis.from_url",
                ],
            },
        },
        "boundaries": {
            "http": {
                "status": "not_detected",
                "detected": False,
                "intercepted": False,
                "simulated": False,
                "faulted": False,
                "unsupported": False,
                "supported_shapes": [],
                "unsupported_details": [],
            },
            "sqlalchemy": {
                "status": "not_detected",
                "detected": False,
                "intercepted": False,
                "simulated": False,
                "faulted": False,
                "unsupported": False,
                "supported_shapes": [],
                "unsupported_details": [],
            },
            "redis": {
                "status": "not_detected",
                "detected": False,
                "intercepted": False,
                "simulated": False,
                "faulted": False,
                "unsupported": False,
                "supported_shapes": [],
                "unsupported_details": [],
            },
        },
    }
