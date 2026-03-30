# WS-06 Semantic Simulators

## Goal

Implement launch-quality semantic simulators for HTTP, SQLAlchemy async, and Redis async.

## Scope

- shared simulator base types
- HTTP response and fault simulation
- SQLAlchemy async semantic state machine
- Redis async semantic state machine

## Out Of Scope

- full backend fidelity
- unsupported backend-specific features beyond launch scope

## Primary Files

- `src/litmus/simulators/base.py`
- `src/litmus/simulators/http.py`
- `src/litmus/simulators/httpx_adapter.py`
- `src/litmus/simulators/aiohttp_adapter.py`
- `src/litmus/simulators/sqlalchemy_async.py`
- `src/litmus/simulators/redis_async.py`

## Dependencies

- WS-05

## Success Criteria

- Common launch faults are reproducible
- CRUD, transaction, caching, and queue-like flows are supported
- Unsupported features fail clearly rather than silently acting real

## Handoff

**Workstream:** WS-06
**Status:** partial, HTTP and SQLAlchemy approved with Redis simulator checkpoint in review
**Files Changed:** `src/litmus/simulators/__init__.py`, `src/litmus/simulators/base.py`, `src/litmus/simulators/http.py`, `src/litmus/simulators/httpx_adapter.py`, `src/litmus/simulators/aiohttp_adapter.py`, `src/litmus/simulators/sqlalchemy_async.py`, `src/litmus/simulators/redis_async.py`, `tests/unit/simulators/test_http_semantics.py`, `tests/unit/simulators/test_sqlalchemy_async.py`, `tests/unit/simulators/test_redis_async.py`, `tests/integration/simulators/test_httpx_adapter.py`, `tests/integration/simulators/test_aiohttp_adapter.py`, `tests/integration/simulators/test_transaction_faults.py`, `tests/integration/simulators/test_redis_faults.py`, `pyproject.toml`, `uv.lock`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`, `git diff --check`
**Results:** WS-06 now has three working slices. The HTTP layer patches real `httpx` and `aiohttp` clients against deterministic fixtures and faults. The SQLAlchemy state machine covers CRUD, read-committed transaction overlays, pool exhaustion, and connection-drop rollback. The new Redis state machine covers string, hash, and list operations, deterministic key expiry via simulated time, blocking `brpop`, and explicit `connection_refused`, `timeout`, `partial_write`, and `MOVED` fault modes.
**Open Risks:** WS-06 is still intentionally narrower than the full launch target. The Redis slice does not yet patch `redis.asyncio`, only supports single-key `brpop`, and rejects pub/sub explicitly instead of simulating it. The SQLAlchemy slice still does not introspect real ORM metadata or simulate richer database failure modes like deadlocks or commit timeouts.
**Next Recommended Step:** Review and stabilize the Redis simulator contract, then decide whether WS-06 should close with the current documented limits or take one more slice for `redis.asyncio` patching and deeper pub/sub behavior.
