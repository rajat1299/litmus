from __future__ import annotations

import json
from pathlib import Path
import subprocess
import textwrap


def test_litmus_replay_replays_a_recorded_breaking_scenario(tmp_path) -> None:
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
                return {"status_code": 500, "json": {"status": "broken"}}
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
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert verify_result.returncode == 1, verify_result.stdout

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Litmus replay" in replay_result.stdout
    assert "Seed: seed:1" in replay_result.stdout
    assert "Route: POST /payments/charge" in replay_result.stdout
    assert "Classification: breaking_change" in replay_result.stdout
    assert "Execution fidelity: matched" in replay_result.stdout
    assert "- Status code regressed from 200 to 500." in replay_result.stdout


def test_litmus_replay_reports_outcome_drift_when_response_body_changes_without_status_change(
    tmp_path: Path,
) -> None:
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
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert verify_result.returncode == 0, verify_result.stdout

    (service_dir / "app.py").write_text(
        (service_dir / "app.py").read_text(encoding="utf-8").replace(
            '{"status": "charged"}',
            '{"status": "delayed"}',
        ),
        encoding="utf-8",
    )

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: benign_change" in replay_result.stdout
    assert "Execution fidelity: drifted" in replay_result.stdout
    assert "- Replay outcome drifted after scheduler decisions and checkpoints aligned." in replay_result.stdout
    assert "- Response body changed from {'status': 'charged'} to {'status': 'delayed'}." in replay_result.stdout


def test_litmus_replay_reports_missing_artifact_cleanly(tmp_path) -> None:
    result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    assert "No replay traces found. Run `litmus verify` first." in result.stderr


def test_litmus_replay_reports_planner_decision_drift_when_current_app_discovers_new_boundary(
    tmp_path: Path,
) -> None:
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
                request = {"method": "GET", "path": "/health"}
                response = {"status_code": 200, "json": {"status": "ok"}}
                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert verify_result.returncode == 0, verify_result.stdout

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json

            import httpx


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
                    await client.get("https://processor.invalid/health")
                return {"status_code": 200, "json": {"status": "ok"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: unchanged" in replay_result.stdout
    assert "Execution fidelity: drifted" in replay_result.stdout
    assert "- Scheduler drift kind: decision_mismatch" in replay_result.stdout
    assert "- Recorded decision 3: probe_targets_discovered (clean_path)" in replay_result.stdout
    assert "- Replay decision 3: probe_targets_discovered (clean_path)" in replay_result.stdout


def test_litmus_replay_reports_unknown_seed_cleanly(tmp_path) -> None:
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
                return {"status_code": 500, "json": {"status": "broken"}}
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
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert verify_result.returncode == 1, verify_result.stdout

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:99"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 1
    assert "No replay trace found for seed:99." in replay_result.stderr


def test_litmus_replay_reports_app_load_error_cleanly(tmp_path: Path) -> None:
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
                return {"status_code": 500, "json": {"status": "broken"}}
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
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert verify_result.returncode == 1, verify_result.stdout

    (service_dir / "app.py").write_text("broken = object()\n", encoding="utf-8")

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 1
    assert "Could not load ASGI app 'service.app:app'" in replay_result.stderr
    assert "Traceback" not in replay_result.stderr


def test_litmus_replay_explains_sqlalchemy_fault_context_from_shipped_verify_path(tmp_path: Path) -> None:
    repo_root = _write_cross_layer_dst_repo(tmp_path)

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert verify_result.returncode == 1, verify_result.stdout

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:2"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: breaking_change" in replay_result.stdout
    assert "Execution fidelity: matched" in replay_result.stdout
    assert "Step 1 scheduled connection_dropped on sqlalchemy." in replay_result.stdout
    assert "Injected connection_dropped on sqlalchemy for begin at step 1." in replay_result.stdout
    assert "Simulated sqlalchemy with Litmus state machines." in replay_result.stdout


def test_litmus_replay_supports_sqlalchemy_orm_sessionmaker_async_constructor(tmp_path: Path) -> None:
    repo_root = _write_cross_layer_dst_repo(tmp_path, sqlalchemy_constructor_shape="orm_sessionmaker")

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert verify_result.returncode == 1, verify_result.stdout

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:2"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: breaking_change" in replay_result.stdout
    assert "Execution fidelity: matched" in replay_result.stdout
    assert "Traceback" not in replay_result.stderr


def test_litmus_replay_supports_direct_sqlalchemy_asyncsession_constructor(tmp_path: Path) -> None:
    repo_root = _write_cross_layer_dst_repo(tmp_path, sqlalchemy_constructor_shape="direct_async_session")

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert verify_result.returncode == 1, verify_result.stdout

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:2"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: breaking_change" in replay_result.stdout
    assert "Execution fidelity: matched" in replay_result.stdout
    assert "Step 1 scheduled connection_dropped on sqlalchemy." in replay_result.stdout
    assert "Injected connection_dropped on sqlalchemy for begin at step 1." in replay_result.stdout
    assert "Simulated sqlalchemy with Litmus state machines." in replay_result.stdout
    assert "Traceback" not in replay_result.stderr


def _write_cross_layer_dst_repo(
    tmp_path: Path,
    *,
    sqlalchemy_constructor_shape: str = "async_sessionmaker",
) -> Path:
    repo_root = tmp_path
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    redis_dir = repo_root / "redis"
    sqlalchemy_dir = repo_root / "sqlalchemy"
    sqlalchemy_ext_dir = sqlalchemy_dir / "ext"
    sqlalchemy_orm_dir = sqlalchemy_dir / "orm"
    service_dir.mkdir()
    tests_dir.mkdir()
    redis_dir.mkdir()
    sqlalchemy_dir.mkdir()
    sqlalchemy_ext_dir.mkdir()
    sqlalchemy_orm_dir.mkdir()

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
    (sqlalchemy_orm_dir / "__init__.py").write_text(
        textwrap.dedent(
            """
            def sessionmaker(*args, **kwargs):
                raise RuntimeError("litmus should patch sqlalchemy.orm.sessionmaker")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    sqlalchemy_import = "from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine"
    sqlalchemy_session_factory = "SessionLocal = async_sessionmaker(engine, expire_on_commit=False)"
    if sqlalchemy_constructor_shape == "orm_sessionmaker":
        sqlalchemy_import = (
            "from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine\n"
            "from sqlalchemy.orm import sessionmaker"
        )
        sqlalchemy_session_factory = (
            "SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)"
        )
    elif sqlalchemy_constructor_shape == "direct_async_session":
        sqlalchemy_import = "from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine"
        sqlalchemy_session_factory = "SessionLocal = AsyncSession"
    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json

            import httpx
            from redis.asyncio import from_url
            from sqlalchemy import Column, MetaData, String, Table, insert, select
            __SQLALCHEMY_IMPORT__


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
            __SQLALCHEMY_SESSION_FACTORY__
            redis = from_url("redis://cache")


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
        .replace("__SQLALCHEMY_IMPORT__", sqlalchemy_import)
        .replace("__SQLALCHEMY_SESSION_FACTORY__", sqlalchemy_session_factory)
        .replace(
            "async with SessionLocal() as session:",
            "async with SessionLocal(engine) as session:"
            if sqlalchemy_constructor_shape == "direct_async_session"
            else "async with SessionLocal() as session:",
        )
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


def test_litmus_replay_reuses_recorded_fault_plan_for_fault_only_breaking_seed(tmp_path: Path) -> None:
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
                        await client.get("https://service.invalid/orders/123")
                    except httpx.HTTPError:
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

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert verify_result.returncode == 1, verify_result.stdout

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: breaking_change" in replay_result.stdout
    assert "- Injected timeout on http for https://service.invalid/orders/123 at step 1." in replay_result.stdout
    assert "No action needed." not in replay_result.stdout

    latest_run_id = json.loads((repo_root / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    replay_run_payload = json.loads(
        (repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8")
    )
    assert replay_run_payload["activities"][0]["summary"]["classification"] == "breaking_change"


def test_litmus_replay_reports_execution_fidelity_drift_even_when_response_is_unchanged(tmp_path: Path) -> None:
    repo_root = _write_replay_fidelity_drift_repo(tmp_path)

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert verify_result.returncode == 0, verify_result.stdout

    (repo_root / "service" / "app.py").write_text(
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
                return {"status_code": 200, "json": {"status": "charged"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: unchanged" in replay_result.stdout
    assert "Execution fidelity: drifted" in replay_result.stdout
    assert "- Replay decisions diverged from the recorded scheduler ledger." in replay_result.stdout
    assert "- Scheduler drift kind: decision_mismatch" in replay_result.stdout
    assert "- Recorded decision 3: probe_targets_discovered (clean_path)" in replay_result.stdout


def _write_replay_fidelity_drift_repo(tmp_path: Path) -> Path:
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

            import httpx


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
                try:
                    async with httpx.AsyncClient() as client:
                        await client.get("https://processor.invalid/charge")
                except Exception:
                    pass
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
