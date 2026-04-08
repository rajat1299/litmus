from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys

from litmus.dst.faults import FaultPlan
from litmus.dst.runtime import RuntimeContext
from litmus.simulators.boundary_patches import (
    _PatchedAsyncEngineProxy,
    _build_patched_asyncsession_constructor,
    _build_patched_orm_sessionmaker,
    _build_patched_redis_constructor,
    activate_runtime,
    patched_supported_boundaries,
)


def test_patched_orm_sessionmaker_preserves_keyword_bind_when_falling_back() -> None:
    captured: dict[str, object] = {}

    def original_sessionmaker(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "original-factory"

    bind = object()
    session_class = object()
    patched = _build_patched_orm_sessionmaker(original_sessionmaker)

    result = patched(bind=bind, class_=session_class, expire_on_commit=False)

    assert result == "original-factory"
    assert captured["args"] == ()
    assert captured["kwargs"] == {
        "bind": bind,
        "class_": session_class,
        "expire_on_commit": False,
    }


def test_patched_asyncsession_constructor_supports_patched_async_engine() -> None:
    class OriginalAsyncSession:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    patched = _build_patched_asyncsession_constructor(OriginalAsyncSession)
    engine = _PatchedAsyncEngineProxy(url="sqlite+aiosqlite:///:memory:", args=(), kwargs={})
    runtime = RuntimeContext(seed=1, fault_plan=FaultPlan(seed=1))

    with activate_runtime(runtime):
        session = patched(engine)

    assert hasattr(session, "execute")
    assert any(
        event.kind == "boundary_intercepted"
        and event.metadata["boundary"] == "sqlalchemy"
        and event.metadata["supported_shape"] == "sqlalchemy.ext.asyncio.AsyncSession"
        for event in runtime.trace
    )


def test_patched_asyncsession_constructor_preserves_type_identity_for_supported_code() -> None:
    class OriginalAsyncSession:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    patched = _build_patched_asyncsession_constructor(OriginalAsyncSession)
    engine = _PatchedAsyncEngineProxy(url="sqlite+aiosqlite:///:memory:", args=(), kwargs={})
    runtime = RuntimeContext(seed=1, fault_plan=FaultPlan(seed=1))

    with activate_runtime(runtime):
        session = patched(engine)

    assert isinstance(patched, type)
    assert isinstance(session, patched)


def test_patched_asyncsession_constructor_preserves_type_identity_inside_async_with() -> None:
    class OriginalAsyncSession:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    async def _exercise() -> None:
        patched = _build_patched_asyncsession_constructor(OriginalAsyncSession)
        engine = _PatchedAsyncEngineProxy(url="sqlite+aiosqlite:///:memory:", args=(), kwargs={})
        runtime = RuntimeContext(seed=1, fault_plan=FaultPlan(seed=1))

        with activate_runtime(runtime):
            async with patched(engine) as session:
                assert isinstance(session, patched)

    asyncio.run(_exercise())


def test_patched_asyncsession_constructor_preserves_keyword_bind_when_falling_back() -> None:
    captured: dict[str, object] = {}

    class OriginalAsyncSession:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

    patched = _build_patched_asyncsession_constructor(OriginalAsyncSession)
    bind = object()

    session = patched(bind=bind, expire_on_commit=False)

    assert isinstance(session, OriginalAsyncSession)
    assert captured["args"] == ()
    assert captured["kwargs"] == {
        "bind": bind,
        "expire_on_commit": False,
    }


def test_patched_supported_boundaries_support_redis_client_module_imports(tmp_path: Path) -> None:
    _clear_test_modules("redis")
    redis_asyncio_dir = tmp_path / "redis" / "asyncio"
    redis_asyncio_dir.mkdir(parents=True)

    (tmp_path / "redis" / "__init__.py").write_text("", encoding="utf-8")
    (redis_asyncio_dir / "__init__.py").write_text(
        (
            "from .client import Redis\n"
            "def from_url(*args, **kwargs):\n"
            "    raise RuntimeError('litmus should patch redis.asyncio.from_url')\n"
        ),
        encoding="utf-8",
    )
    (redis_asyncio_dir / "client.py").write_text(
        (
            "class Redis:\n"
            "    def __init__(self, *args, **kwargs):\n"
            "        raise RuntimeError('litmus should patch redis.asyncio.client.Redis')\n"
            "    @classmethod\n"
            "    def from_url(cls, *args, **kwargs):\n"
            "        raise RuntimeError('litmus should patch redis.asyncio.client.Redis.from_url')\n"
        ),
        encoding="utf-8",
    )

    runtime = RuntimeContext(seed=1, fault_plan=FaultPlan(seed=1))

    async def _exercise() -> None:
        with patched_supported_boundaries(tmp_path):
            client_module = importlib.import_module("redis.asyncio.client")
            with activate_runtime(runtime):
                client = client_module.Redis("redis://cache")
                await client.get("charge:1")
                from_url_client = client_module.Redis.from_url("redis://cache")
                await from_url_client.get("charge:2")

    asyncio.run(_exercise())

    assert any(
        event.kind == "boundary_intercepted"
        and event.metadata["boundary"] == "redis"
        and event.metadata["supported_shape"] == "redis.asyncio.client.Redis"
        for event in runtime.trace
    )
    assert any(
        event.kind == "boundary_intercepted"
        and event.metadata["boundary"] == "redis"
        and event.metadata["supported_shape"] == "redis.asyncio.client.Redis.from_url"
        for event in runtime.trace
    )


def test_patched_redis_constructor_preserves_type_identity_for_supported_code() -> None:
    class OriginalRedis:
        pass

    patched = _build_patched_redis_constructor(
        OriginalRedis,
        supported_shape="redis.asyncio.client.Redis",
        from_url_shape="redis.asyncio.client.Redis.from_url",
    )

    client = patched("redis://cache")
    from_url_client = patched.from_url("redis://cache")

    assert isinstance(patched, type)
    assert isinstance(client, patched)
    assert isinstance(from_url_client, patched)


def _clear_test_modules(*prefixes: str) -> None:
    for name in list(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(name, None)
