# B4 Supported-Stack Fidelity Slice 6 Implementation Plan

**Date:** 2026-04-08  
**Workstream:** WS-23  
**Branch:** `codex/b4-supported-stack-fidelity-slice1`

---

## Bounded Deliverable

Make the supported aiohttp response path transparent enough for ordinary `ClientResponse` use while leaving HTTP simulator behavior and compatibility shapes otherwise unchanged.

---

## Planned Changes

1. Add red tests for `aiohttp.ClientResponse` type identity on the patched aiohttp adapter and in verify/replay-backed aiohttp fixtures.
2. Rework the aiohttp response shim so the supported path returns a `ClientResponse`-shaped object instead of a plain shim.
3. Keep exact HTTP shape reporting as `httpx.AsyncClient` and `aiohttp.ClientSession`.
4. Update grounded compatibility docs to describe the bounded aiohttp response-transparency contract.

---

## Verification

- targeted aiohttp adapter tests for response type identity and basic response use
- targeted verify/replay integration tests with app-level `isinstance(response, aiohttp.ClientResponse)`
- targeted regression packs for HTTP compatibility/reporting surfaces

---

## Review Boundary

Stop after this aiohttp response-transparency slice is implemented, tested, committed, and self-reviewed.

Later WS-23 slices can then choose one next axis only:

- deeper HTTP helper/semantic coverage
- another bounded Redis helper or semantic improvement
- one additional SQLAlchemy helper or semantic gap
