# B4 Supported-Stack Fidelity Slice 2 Design

**Date:** 2026-04-08  
**Status:** slice 2 design  
**Scope:** WS-23 bounded second slice for Track B4

---

## Goal

Broaden Litmus's supported SQLAlchemy async constructor coverage one step further without changing simulator semantics.

This slice adds support for direct async-session construction:

- `sqlalchemy.ext.asyncio.AsyncSession(...)` over a patched async engine

---

## Problem

After slice 1, Litmus supports:

- `sqlalchemy.ext.asyncio.create_async_engine(...)`
- `sqlalchemy.ext.asyncio.async_sessionmaker(...)`
- `sqlalchemy.orm.sessionmaker(..., class_=AsyncSession)`

But a common async app shape still falls outside the supported constructor surface:

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

engine = create_async_engine(...)
session = AsyncSession(engine)
```

That constructor can be backed by the same simulated async-session contract Litmus already uses, but it currently degrades as unsupported.

---

## Slice 2 Contract

1. detect direct `sqlalchemy.ext.asyncio.AsyncSession(...)` usage as a supported SQLAlchemy async boundary shape when it is constructed over a patched async engine
2. patch that constructor path to return the same simulated async session Litmus already uses for the existing SQLAlchemy async factory shapes
3. expose the added supported shape in compatibility artifacts and reporting surfaces
4. preserve unchanged fallback behavior for unsupported AsyncSession constructor calls

---

## Deliberate Non-Goals

This slice does not:

- broaden raw SQL or ORM semantics
- support synchronous SQLAlchemy sessions
- support arbitrary AsyncSession constructor shapes beyond patched-engine use
- widen Redis or HTTP fidelity

Those remain later B4 work.

---

## Exit Criteria

- verify/replay can intercept direct `AsyncSession(...)` construction over a patched async engine
- compatibility artifacts/reporting surface the new SQLAlchemy supported shape honestly
- unsupported AsyncSession constructor shapes still fall back unchanged
