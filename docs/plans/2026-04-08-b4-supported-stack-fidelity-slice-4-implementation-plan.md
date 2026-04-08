# B4 Supported-Stack Fidelity Slice 4 Implementation Plan

**Date:** 2026-04-08  
**Workstream:** WS-23  
**Branch:** `codex/b4-supported-stack-fidelity-slice1`

---

## Bounded Deliverable

Preserve Redis constructor type identity for the already-supported Redis async constructor/import paths while leaving Redis simulator semantics and unsupported Redis variants otherwise unchanged.

---

## Planned Changes

1. Add red tests for Redis type identity on supported constructor/import paths, including app-level `isinstance(redis, Redis)` use.
2. Rework the Redis constructor patch to stay type-shaped on supported paths while still returning Litmus’s simulated proxy behavior.
3. Keep unsupported Redis variants and unsupported-path fallbacks unchanged.
4. Verify the existing compatibility/reporting surfaces still reflect the same bounded supported shapes.

---

## Verification

- targeted boundary-patch unit tests for Redis type identity
- targeted verify/replay integration tests for supported Redis constructors with `isinstance(...)`
- targeted regression pack for shared compatibility/reporting surfaces

---

## Review Boundary

Stop after this constructor-transparency slice is implemented, tested, committed, and self-reviewed.

Later WS-23 slices can then choose one next axis only:

- another bounded Redis helper or semantic improvement
- one HTTP fidelity expansion
- one additional SQLAlchemy helper or semantic gap
