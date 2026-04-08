# B4 Supported-Stack Fidelity Slice 4 Design

**Date:** 2026-04-08  
**Status:** slice 4 design  
**Scope:** WS-23 bounded fourth slice for Track B4

---

## Goal

Preserve Redis client class identity on already-supported constructor/import paths without changing Redis simulator semantics.

This slice keeps the following supported paths usable as types in app code:

- `redis.asyncio.Redis(...)`
- `redis.asyncio.Redis.from_url(...)`
- `redis.asyncio.client.Redis(...)`
- `redis.asyncio.client.Redis.from_url(...)`

---

## Problem

Litmus currently supports the Redis constructor/import paths above, but it patches Redis by replacing the class symbol with a simple constructor wrapper that returns `_PatchedRedisProxy`. That keeps runtime interception working, but ordinary supported code can still drift from real library behavior:

```python
from redis.asyncio.client import Redis

redis = Redis.from_url(...)
assert isinstance(redis, Redis)
```

On the current patch shape, `Redis` stays a class but the returned proxy is not an instance of it, so `isinstance(redis, Redis)` fails even though Litmus advertises the path as supported.

---

## Slice 4 Contract

1. keep already-supported Redis constructor/import paths interceptable
2. preserve Redis class identity for supported code, including `isinstance(redis, Redis)`
3. preserve unchanged fallback behavior for unsupported Redis variants outside the shipped slice
4. avoid broadening Redis command semantics or adding new constructor surfaces

---

## Deliberate Non-Goals

This slice does not:

- add new Redis APIs or command semantics
- support Redis cluster or other unsupported Redis variants
- deepen SQLAlchemy semantics
- broaden HTTP fidelity

Those remain later B4 work.

---

## Exit Criteria

- verify/replay still intercept supported Redis constructor/import paths
- supported Redis code can use `isinstance(redis, Redis)` without type drift
- unsupported Redis variants still degrade explicitly
