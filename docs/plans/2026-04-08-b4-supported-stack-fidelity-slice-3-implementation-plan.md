# B4 Supported-Stack Fidelity Slice 3 Implementation Plan

**Date:** 2026-04-08  
**Workstream:** WS-23  
**Branch:** `codex/b4-supported-stack-fidelity-slice1`

---

## Bounded Deliverable

Support `redis.asyncio.client.Redis(...)` and `redis.asyncio.client.Redis.from_url(...)` while leaving Redis simulator semantics and unsupported Redis variants otherwise unchanged.

---

## Planned Changes

1. Extend Redis boundary detection to recognize the client-module import path as a supported Redis surface.
2. Patch `redis.asyncio.client` alongside `redis.asyncio` so the client-module Redis class resolves to Litmus's existing simulated Redis proxy.
3. Add compatibility/reporting coverage for the new Redis supported shapes.
4. Add targeted unit and integration tests for verify, replay, and honest unsupported fallback.

---

## Verification

- targeted DST engine tests for static Redis boundary detection
- targeted boundary-patch unit tests for Redis client-module constructor behavior
- targeted verify/replay integration tests for the new Redis import path

---

## Review Boundary

Stop after this import-surface expansion is implemented, tested, committed, and self-reviewed.

Later WS-23 slices can then choose one next axis only:

- another Redis helper or constructor path
- deeper Redis semantics
- one HTTP fidelity expansion
- one additional SQLAlchemy helper shape
