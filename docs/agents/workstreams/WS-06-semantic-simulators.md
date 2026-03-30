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
**Status:** partial, HTTP simulator checkpoint in review
**Files Changed:** `src/litmus/simulators/__init__.py`, `src/litmus/simulators/base.py`, `src/litmus/simulators/http.py`, `src/litmus/simulators/httpx_adapter.py`, `src/litmus/simulators/aiohttp_adapter.py`, `tests/unit/simulators/test_http_semantics.py`, `tests/integration/simulators/test_httpx_adapter.py`, `tests/integration/simulators/test_aiohttp_adapter.py`, `pyproject.toml`, `uv.lock`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/unit/simulators/test_http_semantics.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py -q`, `git diff --check`
**Results:** The repo now has a first semantic simulator layer for outbound HTTP. `HttpSimulator` matches method and URL patterns, returns deterministic JSON fixtures, and applies scheduled timeout, connection refusal, HTTP error, and slow-response faults from the WS-05 fault plan. Real `httpx.AsyncClient` and `aiohttp.ClientSession` calls can be patched in-process against those fixtures, then restored to their normal behavior after the test scope ends.
**Open Risks:** This checkpoint only covers HTTP and only the narrow launch fault surface. SQLAlchemy async and Redis async semantics are still unimplemented, and the HTTP adapters do not yet model streaming bodies or deeper client features beyond the tested request path.
**Next Recommended Step:** Review and stabilize the HTTP simulator contracts, then extend WS-06 into SQLAlchemy async and Redis async semantic state machines on top of the current base types and fault-plan interface.
