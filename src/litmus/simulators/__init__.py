from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "DatabaseConnectionDroppedError": (
        "litmus.simulators.sqlalchemy_async",
        "DatabaseConnectionDroppedError",
    ),
    "DatabasePoolExhaustedError": (
        "litmus.simulators.sqlalchemy_async",
        "DatabasePoolExhaustedError",
    ),
    "HttpConnectionRefusedError": ("litmus.simulators.base", "HttpConnectionRefusedError"),
    "HttpSimulator": ("litmus.simulators.http", "HttpSimulator"),
    "HttpTimeoutError": ("litmus.simulators.base", "HttpTimeoutError"),
    "RedisConnectionRefusedError": ("litmus.simulators.redis_async", "RedisConnectionRefusedError"),
    "RedisMovedError": ("litmus.simulators.redis_async", "RedisMovedError"),
    "RedisPartialWriteError": ("litmus.simulators.redis_async", "RedisPartialWriteError"),
    "RedisTimeoutError": ("litmus.simulators.redis_async", "RedisTimeoutError"),
    "SimulatedHttpResponse": ("litmus.simulators.base", "SimulatedHttpResponse"),
    "SimulatedAsyncEngine": ("litmus.simulators.sqlalchemy_async", "SimulatedAsyncEngine"),
    "SimulatedRedis": ("litmus.simulators.redis_async", "SimulatedRedis"),
    "TableSchema": ("litmus.simulators.sqlalchemy_async", "TableSchema"),
    "UnsupportedDatabaseOperationError": (
        "litmus.simulators.sqlalchemy_async",
        "UnsupportedDatabaseOperationError",
    ),
    "UnsupportedRedisOperationError": (
        "litmus.simulators.redis_async",
        "UnsupportedRedisOperationError",
    ),
    "patch_aiohttp": ("litmus.simulators.aiohttp_adapter", "patch_aiohttp"),
    "patch_httpx": ("litmus.simulators.httpx_adapter", "patch_httpx"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = export
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals()) + __all__)
