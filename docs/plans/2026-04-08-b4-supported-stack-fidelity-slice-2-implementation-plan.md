# B4 Supported-Stack Fidelity Slice 2 Implementation Plan

**Date:** 2026-04-08  
**Workstream:** WS-23  
**Branch:** `codex/b4-supported-stack-fidelity-slice1`

---

## Bounded Deliverable

Support direct `sqlalchemy.ext.asyncio.AsyncSession(...)` construction over a patched async engine while leaving SQLAlchemy simulator semantics and unsupported constructor behavior otherwise unchanged.

---

## Planned Changes

1. Extend SQLAlchemy boundary detection to recognize direct AsyncSession construction as a supported async shape when used with the patched-engine path.
2. Patch `sqlalchemy.ext.asyncio.AsyncSession` to return Litmus's simulated async session only for the patched-engine shape.
3. Add compatibility/reporting coverage for the new supported shape.
4. Add targeted unit and integration tests for verify, replay, and fallback behavior.

---

## Verification

- targeted DST engine tests for static boundary detection
- targeted boundary-patch unit tests for supported and unsupported AsyncSession constructor behavior
- targeted verify/replay integration tests for the new constructor path

---

## Review Boundary

Stop after this constructor-surface expansion is implemented, tested, committed, and self-reviewed.

Later WS-23 slices can then choose one next axis only:

- another SQLAlchemy constructor/helper shape
- deeper SQLAlchemy semantics
- one Redis or HTTP fidelity expansion
