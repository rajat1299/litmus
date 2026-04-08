# B4 Supported-Stack Fidelity Slice 7 Implementation Plan

**Date:** 2026-04-08  
**Workstream:** WS-23  
**Branch:** `codex/b4-supported-stack-fidelity-slice1`

---

## Bounded Deliverable

Make the already-supported Redis async constructor/import paths lifecycle-transparent enough for ordinary `async with` and `aclose()` use while leaving Redis simulator behavior and compatibility shapes otherwise unchanged.

---

## Planned Changes

1. Add a red unit test on the patched Redis constructor path for `async with Redis.from_url(...) as redis` plus explicit `await redis.aclose()`.
2. Add one verify-level and one replay-level regression on an already-supported Redis constructor path that uses both context-manager entry/exit and explicit close.
3. Extend `_PatchedRedisProxy` to implement `__aenter__`, `__aexit__`, and `aclose()` with `__aexit__` delegating to `await self.aclose()`.
4. Update grounded compatibility/status docs to describe the bounded Redis lifecycle-transparency contract honestly.

---

## Verification

- targeted boundary-patch unit coverage for Redis lifecycle hooks
- targeted verify and replay regressions for the supported Redis lifecycle path
- bounded B4 Redis/HTTP/SQLAlchemy regression pack after the fix

---

## Review Boundary

Stop after this Redis lifecycle-transparency slice is implemented, tested, committed, and self-reviewed.

Later WS-23 slices can then choose one next axis only:

- deeper Redis semantic fidelity
- another bounded HTTP transparency/helper improvement
- one additional SQLAlchemy semantic gap
