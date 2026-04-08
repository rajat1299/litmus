# B4 Supported-Stack Fidelity Slice 3 Design

**Date:** 2026-04-08  
**Status:** slice 3 design  
**Scope:** WS-23 bounded third slice for Track B4

---

## Goal

Broaden Litmus's supported Redis async import coverage one step further without changing Redis simulator semantics.

This slice adds support for common client-module Redis imports:

- `redis.asyncio.client.Redis(...)`
- `redis.asyncio.client.Redis.from_url(...)`

---

## Problem

After the current B4 slices, Litmus supports:

- `redis.asyncio.Redis(...)`
- `redis.asyncio.Redis.from_url(...)`
- `redis.asyncio.from_url(...)`

But a common real-world import shape still falls outside the supported surface:

```python
from redis.asyncio.client import Redis

redis = Redis(...)
```

and similarly:

```python
from redis.asyncio.client import Redis

redis = Redis.from_url(...)
```

Those shapes can be backed by the same simulated Redis proxy Litmus already uses, but they currently degrade as unsupported because static detection and monkeypatch coverage are tied to `redis.asyncio`.

---

## Slice 3 Contract

1. detect `redis.asyncio.client.Redis(...)` and `redis.asyncio.client.Redis.from_url(...)` as supported Redis boundary shapes
2. patch the relevant Redis client-module import surface to return the same simulated Redis proxy Litmus already uses
3. expose the added supported shapes in compatibility artifacts and reporting surfaces
4. preserve unchanged fallback behavior for unsupported Redis types such as `RedisCluster`

---

## Deliberate Non-Goals

This slice does not:

- deepen Redis command semantics
- support Redis cluster/client variants beyond the common `client.Redis` import path
- broaden HTTP fidelity
- widen SQLAlchemy semantics beyond the already landed constructor-path slices

Those remain later B4 work.

---

## Exit Criteria

- verify/replay can intercept `redis.asyncio.client.Redis(...)` and `redis.asyncio.client.Redis.from_url(...)`
- compatibility artifacts/reporting surface the new Redis supported shapes honestly
- unsupported Redis variants still degrade explicitly
