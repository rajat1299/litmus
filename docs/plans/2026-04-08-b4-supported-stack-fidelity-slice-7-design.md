# B4 Supported-Stack Fidelity Slice 7 Design

**Date:** 2026-04-08  
**Status:** slice 7 design  
**Scope:** WS-23 bounded seventh slice for Track B4

---

## Goal

Preserve ordinary Redis async lifecycle use on the already-supported Redis constructor/import paths without changing Redis simulator semantics.

This slice stays on an existing supported path and removes another "supported but shape-broken" gap, similar to the earlier SQLAlchemy, Redis type-identity, and aiohttp response-transparency slices.

---

## Problem

Litmus already supports the shipped Redis async constructor/import shapes, but the patched Redis proxy is still missing common lifecycle hooks:

```python
async with Redis.from_url("redis://cache") as redis:
    await redis.get("charge:1")

await redis.aclose()
```

Today that path remains interceptable for ordinary method calls, but it is not yet lifecycle-transparent on the supported slice because the proxy does not implement `__aenter__`, `__aexit__`, or `aclose()`.

---

## Slice 7 Contract

1. keep current Redis simulator semantics unchanged
2. keep the supported Redis constructor/import matrix unchanged:
   - `redis.asyncio.Redis(...)`
   - `redis.asyncio.Redis.from_url(...)`
   - `redis.asyncio.client.Redis(...)`
   - `redis.asyncio.client.Redis.from_url(...)`
3. on the supported Redis async path, preserve:
   - `isinstance(redis, Redis)` on already-supported paths
   - `async with redis as cache`
   - `async with Redis.from_url(...) as cache`
   - `await redis.aclose()`
4. make `__aexit__` delegate to `await self.aclose()` so explicit close and context-manager exit share one lifecycle path

---

## Deliberate Non-Goals

This slice does not:

- add new Redis constructor or import shapes
- change planner behavior or Redis fault targeting
- add pipeline, pub/sub, cluster, or connection-pool semantics
- claim full Redis client fidelity beyond the bounded lifecycle hooks

Those remain later B4 work if needed.

---

## Exit Criteria

- supported Redis async paths remain interceptable
- `async with` and `await redis.aclose()` work on the supported Redis slice
- type identity still holds on the already-supported Redis constructor paths
- unsupported Redis variants still degrade unchanged
