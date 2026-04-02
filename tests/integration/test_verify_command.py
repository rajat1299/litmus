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
            "unchanged": 6,
            "breaking_change": 0,
            "benign_change": 0,
            "improvement": 0,
        },
        "properties": {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        },
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
    assert summary["replay"]["unchanged"] == 3


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


def _latest_verify_summary(repo_root: Path) -> dict:
    latest_run_id = json.loads((repo_root / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))
    return run_payload["activities"][0]["summary"]
