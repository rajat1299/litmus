# B4 Supported-Stack Fidelity Slice 5 Implementation Plan

**Date:** 2026-04-08  
**Workstream:** WS-23  
**Branch:** `codex/b4-supported-stack-fidelity-slice1`

---

## Bounded Deliverable

Make Litmus's HTTP compatibility contract more precise by recording exact `httpx` versus `aiohttp` supported shapes and by adding shipped verify/replay coverage for the aiohttp path.

---

## Planned Changes

1. Add red tests for exact HTTP supported-shape reporting and for an aiohttp-backed verify/replay fixture.
2. Update the HTTP simulator and adapters to record shape-specific compatibility metadata without changing fault behavior.
3. Update shared compatibility/reporting surfaces to expose the refined HTTP shapes honestly.
4. Verify the existing httpx path still behaves the same after the reporting change.

---

## Verification

- targeted unit tests for shared compatibility/reporting surfaces
- targeted verify/replay integration tests for aiohttp-backed fixtures
- targeted regression pack covering existing httpx plus the new aiohttp reporting path

---

## Review Boundary

Stop after this HTTP client-shape fidelity slice is implemented, tested, committed, and self-reviewed.

Later WS-23 slices can then choose one next axis only:

- deeper HTTP helper/semantic coverage
- another bounded Redis helper or semantic improvement
- one additional SQLAlchemy helper or semantic gap
