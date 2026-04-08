from __future__ import annotations

import asyncio

from litmus.dst.faults import FaultPlan
from litmus.dst.runtime import RuntimeContext
from litmus.simulators.boundary_patches import (
    _PatchedAsyncEngineProxy,
    _build_patched_asyncsession_constructor,
    _build_patched_orm_sessionmaker,
    activate_runtime,
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
