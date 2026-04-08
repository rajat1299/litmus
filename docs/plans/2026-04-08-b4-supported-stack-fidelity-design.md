# B4 Supported-Stack Fidelity Design

**Date:** 2026-04-08  
**Status:** slice 1 design  
**Scope:** WS-23 bounded first slice for Track B4

---

## Goal

Broaden Litmus's supported constructor surface without widening simulator claims beyond what the runtime can honestly intercept today.

The first slice stays narrow:

- add support for the common SQLAlchemy async factory path `sqlalchemy.orm.sessionmaker(..., class_=AsyncSession)`
- keep the simulator contract unchanged underneath that new factory shape
- expose the new supported shape in compatibility/reporting surfaces

---

## Problem

Litmus currently supports SQLAlchemy only through:

- `sqlalchemy.ext.asyncio.create_async_engine(...)`
- `sqlalchemy.ext.asyncio.async_sessionmaker(...)`

That is narrower than many real async apps. A common SQLAlchemy pattern is:

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(...)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

Today that shape falls outside the supported launch slice even though Litmus already has the core async engine/session simulator needed to back it.

---

## Slice 1 Contract

Add a Litmus-native compatibility expansion for one additional SQLAlchemy constructor surface:

1. detect `sqlalchemy.orm.sessionmaker(..., class_=AsyncSession)` as a supported SQLAlchemy boundary shape
2. patch that factory path to produce the same simulated async sessions Litmus already uses for `async_sessionmaker`
3. persist/report the added supported shape alongside existing SQLAlchemy compatibility data

The simulator itself does not become broader in this slice. The change is constructor-surface coverage, not a new SQLAlchemy semantics tier.

---

## Source Of Truth

The source of truth remains Litmus-native:

- AST boundary detection decides whether the app uses the newly supported shape
- runtime monkeypatches decide whether Litmus can actually intercept the shape
- compatibility/reporting surfaces derive from runtime trace events, not from docs alone

Claude Code patterns remain irrelevant to the simulation logic itself.

---

## Deliberate Non-Goals

This slice does not:

- broaden raw SQL support
- add multi-table ORM semantics
- support arbitrary `sqlalchemy.orm.sessionmaker` shapes beyond `class_=AsyncSession`
- add synchronous SQLAlchemy support
- broaden Redis or HTTP constructor coverage

Those belong to later B4 slices once this constructor expansion is reviewed.

---

## Exit Criteria

- verify/replay can intercept the common `sqlalchemy.orm.sessionmaker(..., class_=AsyncSession)` async path
- compatibility artifacts/reporting surface the new SQLAlchemy supported shape honestly
- unsupported SQLAlchemy shapes still degrade explicitly
