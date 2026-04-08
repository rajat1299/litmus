# B4 Supported-Stack Fidelity Slice 6 Design

**Date:** 2026-04-08  
**Status:** slice 6 design  
**Scope:** WS-23 bounded sixth slice for Track B4

---

## Goal

Preserve ordinary `aiohttp.ClientResponse` use on the already-supported `aiohttp.ClientSession` path without changing HTTP simulator semantics.

This slice keeps the current shipped HTTP compatibility contract intact while making the returned aiohttp response object more transparent for supported code.

---

## Problem

Litmus already supports outbound aiohttp requests on the `aiohttp.ClientSession` path, but the simulated response object is still a plain shim rather than a `ClientResponse`-shaped object. That means supported code can be subtly shape-broken even though request interception and faulting work:

```python
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        assert isinstance(response, aiohttp.ClientResponse)
```

The current path keeps `status`, `json()`, `text()`, and `read()` usable, but it does not yet preserve ordinary response-type use on an already-supported path.

---

## Slice 6 Contract

1. keep current HTTP simulator semantics unchanged
2. keep exact compatibility reporting as `httpx.AsyncClient` and `aiohttp.ClientSession`
3. on the supported aiohttp path, preserve:
   - `isinstance(response, aiohttp.ClientResponse)`
   - `response.status`
   - `await response.json()`
   - `await response.text()`
   - `await response.read()`
   - basic `headers` lookup already exposed by the simulator path
4. keep anything beyond that outside the bounded slice unless it is naturally preserved

---

## Deliberate Non-Goals

This slice does not:

- add new HTTP helper surfaces
- change HTTP fault kinds or planner behavior
- broaden Redis or SQLAlchemy semantics
- claim full `aiohttp.ClientResponse` fidelity

Those remain later B4 work if needed.

---

## Exit Criteria

- supported aiohttp response objects preserve `ClientResponse` type identity
- verify/replay exercise the supported aiohttp path with app-level response type guards
- HTTP simulator semantics and exact client-shape reporting remain unchanged
