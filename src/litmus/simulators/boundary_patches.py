from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
import importlib
import sys
from pathlib import Path
from typing import Any
from itertools import count

from litmus.dst.runtime import RuntimeContext
from litmus.simulators.redis_async import SimulatedRedis
from litmus.simulators.sqlalchemy_async import SimulatedAsyncEngine, TableSchema

_CURRENT_RUNTIME: ContextVar[RuntimeContext | None] = ContextVar("litmus_current_runtime", default=None)
_PROXY_IDS = count(1)


@contextmanager
def activate_runtime(runtime: RuntimeContext):
    token = _CURRENT_RUNTIME.set(runtime)
    try:
        yield
    finally:
        _CURRENT_RUNTIME.reset(token)


def current_runtime() -> RuntimeContext | None:
    return _CURRENT_RUNTIME.get()


@contextmanager
def patched_supported_boundaries(root: Path | str | None = None):
    patchers: list[_ModulePatch] = []
    with _temporary_import_root(root):
        sqlalchemy_patch = _patch_sqlalchemy_async()
        if sqlalchemy_patch is not None:
            patchers.append(sqlalchemy_patch)
        sqlalchemy_orm_patch = _patch_sqlalchemy_orm()
        if sqlalchemy_orm_patch is not None:
            patchers.append(sqlalchemy_orm_patch)
        redis_patch = _patch_redis_async()
        if redis_patch is not None:
            patchers.append(redis_patch)
        try:
            yield
        finally:
            for patcher in reversed(patchers):
                patcher.restore()


class _ModulePatch:
    def __init__(self, module, original: dict[str, object]) -> None:
        self._module = module
        self._original = original

    def restore(self) -> None:
        for name, value in self._original.items():
            setattr(self._module, name, value)


def _patch_sqlalchemy_async() -> _ModulePatch | None:
    try:
        module = importlib.import_module("sqlalchemy.ext.asyncio")
    except ImportError:
        return None

    original: dict[str, object] = {}

    if hasattr(module, "create_async_engine"):
        original["create_async_engine"] = module.create_async_engine
        module.create_async_engine = _patched_create_async_engine

    if hasattr(module, "AsyncSession"):
        original["AsyncSession"] = module.AsyncSession
        module.AsyncSession = _build_patched_asyncsession_constructor(module.AsyncSession)

    if hasattr(module, "async_sessionmaker"):
        original["async_sessionmaker"] = module.async_sessionmaker
        module.async_sessionmaker = _patched_async_sessionmaker

    return _ModulePatch(module, original)


def _patch_sqlalchemy_orm() -> _ModulePatch | None:
    try:
        module = importlib.import_module("sqlalchemy.orm")
    except ImportError:
        return None

    original: dict[str, object] = {}

    if hasattr(module, "sessionmaker"):
        original["sessionmaker"] = module.sessionmaker
        module.sessionmaker = _build_patched_orm_sessionmaker(module.sessionmaker)

    return _ModulePatch(module, original)


def _patch_redis_async() -> _ModulePatch | None:
    try:
        module = importlib.import_module("redis.asyncio")
    except ImportError:
        return None

    original: dict[str, object] = {}

    if hasattr(module, "Redis"):
        original["Redis"] = module.Redis
        module.Redis = _PatchedRedisConstructor

    if hasattr(module, "from_url"):
        original["from_url"] = module.from_url
        module.from_url = _PatchedRedisConstructor.from_url

    return _ModulePatch(module, original)


def _patched_create_async_engine(url: str, *args, **kwargs):
    return _PatchedAsyncEngineProxy(url=url, args=args, kwargs=kwargs)


def _patched_async_sessionmaker(bind, *args, **kwargs):
    if isinstance(bind, _PatchedAsyncEngineProxy):
        return _PatchedAsyncSessionFactory(
            bind,
            args=args,
            kwargs=kwargs,
            supported_shape="sqlalchemy.ext.asyncio.async_sessionmaker",
        )

    raise RuntimeError("Litmus only supports async_sessionmaker with a patched async engine in this slice.")


def _build_patched_asyncsession_constructor(original_async_session):
    original_meta = type(original_async_session)

    class _PatchedAsyncSessionMeta(original_meta):
        def __call__(cls, *args, **kwargs):
            resolved_bind = args[0] if args else kwargs.get("bind")
            if isinstance(resolved_bind, _PatchedAsyncEngineProxy) and current_runtime() is not None:
                return _PatchedAsyncSession(
                    resolved_bind,
                    supported_shape="sqlalchemy.ext.asyncio.AsyncSession",
                )
            return original_async_session(*args, **kwargs)

        def __instancecheck__(cls, instance):
            return isinstance(instance, _PatchedAsyncSession) or isinstance(instance, original_async_session)

        def __subclasscheck__(cls, subclass):
            return subclass is _PatchedAsyncSession or issubclass(subclass, original_async_session)

    return _PatchedAsyncSessionMeta(
        getattr(original_async_session, "__name__", "AsyncSession"),
        (original_async_session,),
        {
            "__doc__": getattr(original_async_session, "__doc__", None),
            "__module__": getattr(original_async_session, "__module__", __name__),
            "__qualname__": getattr(
                original_async_session,
                "__qualname__",
                getattr(original_async_session, "__name__", "AsyncSession"),
            ),
        },
    )


def _build_patched_orm_sessionmaker(original_sessionmaker):
    def _patched_orm_sessionmaker(*args, **kwargs):
        resolved_bind = args[0] if args else kwargs.get("bind")
        if isinstance(resolved_bind, _PatchedAsyncEngineProxy) and _uses_sqlalchemy_asyncsession(kwargs):
            return _PatchedAsyncSessionFactory(
                resolved_bind,
                args=args,
                kwargs=kwargs,
                supported_shape="sqlalchemy.orm.sessionmaker(class_=AsyncSession)",
            )
        return original_sessionmaker(*args, **kwargs)

    return _patched_orm_sessionmaker


def _uses_sqlalchemy_asyncsession(kwargs: dict[str, object]) -> bool:
    async_session_class = kwargs.get("class_")
    if async_session_class is None:
        return False
    try:
        module = importlib.import_module("sqlalchemy.ext.asyncio")
    except ImportError:
        return False
    expected_class = getattr(module, "AsyncSession", None)
    return expected_class is not None and async_session_class is expected_class


class _PatchedRedisConstructor:
    def __new__(cls, *args, **kwargs):
        return _PatchedRedisProxy(
            supported_shape="redis.asyncio.Redis",
            args=args,
            kwargs=kwargs,
        )

    @classmethod
    def from_url(cls, url: str, *args, **kwargs):
        return _PatchedRedisProxy(
            supported_shape="redis.asyncio.Redis.from_url",
            args=(url, *args),
            kwargs=kwargs,
        )


class _PatchedAsyncEngineProxy:
    def __init__(self, *, url: str, args: tuple[object, ...], kwargs: dict[str, object]) -> None:
        self.url = url
        self.args = args
        self.kwargs = kwargs
        self.proxy_id = next(_PROXY_IDS)

    async def dispose(self) -> None:
        return None

    def simulator_for_runtime(self, runtime: RuntimeContext) -> SimulatedAsyncEngine:
        runtime.mark_boundary_detected("sqlalchemy", detail=self.url)
        runtime.mark_boundary_intercepted(
            "sqlalchemy",
            supported_shape="sqlalchemy.ext.asyncio.create_async_engine",
        )
        runtime.mark_boundary_simulated("sqlalchemy")
        cache_key = ("sqlalchemy", self.proxy_id)
        engine = runtime.resources.get(cache_key)
        if isinstance(engine, SimulatedAsyncEngine):
            return engine
        engine = SimulatedAsyncEngine(
            schemas={},
            fault_plan=runtime.fault_plan,
            record_event=runtime.record,
        )
        runtime.resources[cache_key] = engine
        return engine


class _PatchedAsyncSessionFactory:
    def __init__(
        self,
        engine: _PatchedAsyncEngineProxy,
        *,
        args: tuple[object, ...],
        kwargs: dict[str, object],
        supported_shape: str,
    ) -> None:
        self._engine = engine
        self._args = args
        self._kwargs = kwargs
        self._supported_shape = supported_shape

    def __call__(self, *args, **kwargs):
        return _PatchedAsyncSession(self._engine, supported_shape=self._supported_shape)


class _PatchedAsyncSession:
    def __init__(self, engine: _PatchedAsyncEngineProxy, *, supported_shape: str) -> None:
        runtime = _require_runtime("sqlalchemy")
        self._engine = engine
        self._runtime = runtime
        simulator = engine.simulator_for_runtime(runtime)
        runtime.mark_boundary_intercepted("sqlalchemy", supported_shape=supported_shape)
        self._session = simulator.session()

    async def __aenter__(self):
        await self._session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return await self._session.__aexit__(exc_type, exc, tb)

    async def begin(self) -> None:
        await self._session.begin()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def execute(self, statement):
        statement_type = getattr(statement, "__litmus_statement_type__", None)
        if statement_type == "insert":
            table = statement.table
            _ensure_simulated_table(self._engine.simulator_for_runtime(self._runtime), table)
            await self._session.insert(table.name, dict(getattr(statement, "values_dict", {})))
            return _PatchedQueryResult([])

        if statement_type == "select":
            table = statement.table
            _ensure_simulated_table(self._engine.simulator_for_runtime(self._runtime), table)
            filter_condition = getattr(statement, "filter", None)
            primary_key = None if filter_condition is None else getattr(filter_condition, "value", None)
            if primary_key is None:
                rows = await self._session.all(table.name)
            else:
                row = await self._session.get(table.name, primary_key)
                rows = [] if row is None else [row]
            return _PatchedQueryResult(rows)

        try:
            from sqlalchemy.sql.dml import Delete, Insert, Update
            from sqlalchemy.sql.selectable import Select
        except ImportError as exc:  # pragma: no cover - import is available in supported test env
            raise RuntimeError("SQLAlchemy is required for Litmus SQLAlchemy interception.") from exc

        if isinstance(statement, Insert):
            _ensure_simulated_table(self._engine.simulator_for_runtime(self._runtime), statement.table)
            await self._session.insert(statement.table.name, dict(statement.compile().params))
            return _PatchedQueryResult([])

        if isinstance(statement, Select):
            table = _extract_single_table(statement)
            _ensure_simulated_table(self._engine.simulator_for_runtime(self._runtime), table)
            primary_key = _extract_primary_key_value(statement)
            if primary_key is None:
                rows = await self._session.all(table.name)
            else:
                row = await self._session.get(table.name, primary_key)
                rows = [] if row is None else [row]
            return _PatchedQueryResult(rows)

        if isinstance(statement, Update):
            _ensure_simulated_table(self._engine.simulator_for_runtime(self._runtime), statement.table)
            values = dict(statement.compile().params)
            primary_key = _extract_primary_key_value(statement)
            filter_param_name = _filter_param_name(statement)
            if filter_param_name is not None:
                values.pop(filter_param_name, None)
            if primary_key is None:
                raise RuntimeError("Litmus only supports primary-key equality updates in this slice.")
            await self._session.update(statement.table.name, primary_key, values)
            return _PatchedQueryResult([])

        if isinstance(statement, Delete):
            _ensure_simulated_table(self._engine.simulator_for_runtime(self._runtime), statement.table)
            primary_key = _extract_primary_key_value(statement)
            if primary_key is None:
                raise RuntimeError("Litmus only supports primary-key equality deletes in this slice.")
            await self._session.delete(statement.table.name, primary_key)
            return _PatchedQueryResult([])

        return await self._session.execute(str(statement))


class _PatchedQueryResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def first(self):
        return None if not self._rows else self._rows[0]

    def all(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return None if not self._rows else self._rows[0]


class _PatchedRedisProxy:
    def __init__(self, *, supported_shape: str, args: tuple[object, ...], kwargs: dict[str, object]) -> None:
        self._supported_shape = supported_shape
        self._args = args
        self._kwargs = kwargs
        self._proxy_id = next(_PROXY_IDS)

    def _client(self) -> SimulatedRedis:
        runtime = _require_runtime("redis")
        runtime.mark_boundary_detected("redis")
        runtime.mark_boundary_intercepted("redis", supported_shape=self._supported_shape)
        runtime.mark_boundary_simulated("redis")
        cache_key = ("redis", self._proxy_id)
        client = runtime.resources.get(cache_key)
        if isinstance(client, SimulatedRedis):
            return client
        client = SimulatedRedis(
            fault_plan=runtime.fault_plan,
            record_event=runtime.record,
        )
        runtime.resources[cache_key] = client
        return client

    def __getattr__(self, name: str):
        return getattr(self._client(), name)


def _ensure_simulated_table(engine: SimulatedAsyncEngine, table) -> None:
    if table.name in engine._schemas:  # noqa: SLF001 - simulator internals are the compatibility surface here
        return

    primary_key_column = next(iter(table.primary_key.columns), None)
    if primary_key_column is None:
        raise RuntimeError(f"Litmus requires a primary key to simulate table {table.name!r}.")
    engine._schemas[table.name] = TableSchema(  # noqa: SLF001
        primary_key=primary_key_column.name,
        columns=tuple(column.name for column in table.columns),
    )
    engine._state.setdefault(table.name, {})  # noqa: SLF001


def _extract_single_table(statement):
    table = next(iter(statement.get_final_froms()), None)
    if table is None:
        raise RuntimeError("Litmus only supports single-table selects in this slice.")
    return table


def _extract_primary_key_value(statement) -> object | None:
    criteria = list(getattr(statement, "_where_criteria", ()))
    if not criteria:
        return None
    criterion = criteria[0]
    right = getattr(criterion, "right", None)
    return getattr(right, "value", None)


def _filter_param_name(statement) -> str | None:
    criteria = list(getattr(statement, "_where_criteria", ()))
    if not criteria:
        return None
    right = getattr(criteria[0], "right", None)
    return getattr(right, "key", None)


def _require_runtime(boundary: str) -> RuntimeContext:
    runtime = current_runtime()
    if runtime is None:
        raise RuntimeError(f"Litmus has no active runtime while servicing {boundary}.")
    return runtime


@contextmanager
def _temporary_import_root(root: Path | str | None):
    if root is None:
        importlib.invalidate_caches()
        yield
        return

    root_path = str(Path(root).resolve())
    already_present = root_path in sys.path
    if not already_present:
        sys.path.insert(0, root_path)
    importlib.invalidate_caches()
    try:
        yield
    finally:
        if not already_present:
            sys.path.remove(root_path)
        importlib.invalidate_caches()
