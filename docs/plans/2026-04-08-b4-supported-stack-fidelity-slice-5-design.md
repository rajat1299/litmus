# B4 Supported-Stack Fidelity Slice 5 Design

**Date:** 2026-04-08  
**Status:** slice 5 design  
**Scope:** WS-23 bounded fifth slice for Track B4

---

## Goal

Make Litmus's shipped HTTP support more explicit and better tested without changing HTTP simulator semantics.

This slice narrows the currently coarse HTTP compatibility contract by distinguishing:

- `httpx.AsyncClient`
- `aiohttp.ClientSession`

and by adding verify/replay coverage for the aiohttp path that Litmus already claims to support.

---

## Problem

Litmus currently reports the HTTP boundary as a single generic supported shape, `httpx/aiohttp`. That is too coarse for two reasons:

1. it does not tell the user which HTTP client family Litmus actually intercepted
2. verify/replay integration coverage is currently concentrated on `httpx`, so the shipped `aiohttp` claim is less exercised than the Redis and SQLAlchemy shapes added in recent B4 slices

That leaves HTTP support less grounded than the rest of the B4 compatibility surface.

---

## Slice 5 Contract

1. preserve the existing HTTP simulator behavior
2. record exact shipped HTTP client shapes in compatibility/reporting surfaces
3. add verify/replay coverage for the `aiohttp.ClientSession` path
4. keep unsupported or deeper HTTP semantics outside this slice

---

## Deliberate Non-Goals

This slice does not:

- change HTTP fault semantics
- add new outbound HTTP APIs beyond the shipped `httpx` and `aiohttp` client families
- broaden Redis or SQLAlchemy semantics
- attempt top-level helper coverage such as every `httpx.*` convenience function

Those remain later B4 work if needed.

---

## Exit Criteria

- compatibility/reporting surfaces distinguish `httpx.AsyncClient` and `aiohttp.ClientSession`
- verify/replay coverage exists for the aiohttp shipped path
- current HTTP simulator semantics remain unchanged
