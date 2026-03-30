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
