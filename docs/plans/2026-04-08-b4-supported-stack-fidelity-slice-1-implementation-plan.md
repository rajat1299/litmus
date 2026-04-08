# B4 Supported-Stack Fidelity Slice 1 Implementation Plan

**Date:** 2026-04-08  
**Workstream:** WS-23  
**Branch:** `codex/b4-supported-stack-fidelity-slice1`

---

## Bounded Deliverable

Support the common SQLAlchemy async factory shape `sqlalchemy.orm.sessionmaker(..., class_=AsyncSession)` while keeping simulator semantics and unsupported-shape behavior otherwise unchanged.

---

## Planned Changes

1. Extend SQLAlchemy boundary detection to recognize `sqlalchemy.orm.sessionmaker(..., class_=AsyncSession)` as a supported async shape.
2. Patch `sqlalchemy.orm.sessionmaker` when it is configured for `AsyncSession` over a patched async engine.
3. Record/report the added supported shape through compatibility artifacts, CLI summaries, and run/MCP projections.
4. Add targeted unit and integration coverage for verify-path interception and compatibility reporting.

---

## Verification

- targeted DST engine tests for shape detection and runtime planner behavior
- targeted verify/replay integration tests proving the new sessionmaker shape is intercepted end-to-end
- targeted summary/compatibility assertions for the added supported shape

---

## Review Boundary

Stop after this constructor-surface expansion is implemented, tested, committed, and self-reviewed.

Later B4 slices can then decide whether to:

- broaden more SQLAlchemy shapes
- deepen SQLAlchemy semantics
- expand Redis or HTTP constructor coverage
