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
**Status:** partial, HTTP approved and SQLAlchemy simulator checkpoint in review
**Files Changed:** `src/litmus/simulators/__init__.py`, `src/litmus/simulators/base.py`, `src/litmus/simulators/http.py`, `src/litmus/simulators/httpx_adapter.py`, `src/litmus/simulators/aiohttp_adapter.py`, `src/litmus/simulators/sqlalchemy_async.py`, `tests/unit/simulators/test_http_semantics.py`, `tests/unit/simulators/test_sqlalchemy_async.py`, `tests/integration/simulators/test_httpx_adapter.py`, `tests/integration/simulators/test_aiohttp_adapter.py`, `tests/integration/simulators/test_transaction_faults.py`, `pyproject.toml`, `uv.lock`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py -q`, `git diff --check`
**Results:** WS-06 now has two stable slices. The HTTP layer remains the approved outbound-call simulator with real `httpx` and `aiohttp` patching. The new SQLAlchemy async state machine models table state as in-memory primary-key dictionaries, supports insert/select/update/delete plus transaction begin/commit/rollback with read-committed visibility, enforces pool limits, and rolls back staged writes when a scheduled `connection_dropped` fault interrupts a transaction.
**Open Risks:** Redis async semantics are still unimplemented. The SQLAlchemy slice is intentionally narrower than the full launch target: it does not yet introspect real ORM metadata, patch `sqlalchemy.ext.asyncio`, or simulate deadlocks, commit timeouts, joins, or other richer database behavior beyond the tested CRUD and transaction path.
**Next Recommended Step:** Review and stabilize the SQLAlchemy simulator contract, then implement the Redis async semantic state machine and fault surface before revisiting deeper SQLAlchemy fidelity or real-library patching.
