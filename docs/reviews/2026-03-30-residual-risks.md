# Residual Risks Through WS-06 Reviews

**Status Date:** 2026-03-30
**Scope:** Residual risks and open limitations that still remain after the reviewed WS-01 through WS-06 checkpoints. This list excludes findings that were already fixed during review.

## Purpose

This document captures the risks that still matter after the current review loop so later workstreams do not lose context when they move into DST runtime, reporting, watch mode, and release packaging.

## WS-01 Repo And CLI Foundation

### R-WS01-1 Thin CLI coverage

The current smoke coverage is still shallow. The bootstrap tests validate the `litmus --help` surface, but they do not yet exercise placeholder command behavior in a meaningful way. This is acceptable for the bootstrap slice, but it leaves command wiring regressions easy to miss until `verify`, `watch`, and `replay` gain real behavior.

### R-WS01-2 Version metadata drift

Package version metadata is duplicated across packaging and module code. That is not breaking today, but it creates an avoidable drift point once release packaging and automation start depending on version correctness.

## WS-02 App Discovery, Diff Tracing, And Endpoint Mapping

### R-WS02-1 Module cache bleed across repo roots

ASGI app loading is now repo-root aware, but Python module caching still means same-named modules can be reused across different repo roots inside one long-lived process. The current CLI contract is effectively one repo per process, so this is acceptable for now. It becomes a real risk if Litmus grows into a daemon, server, or multi-repo worker.

### R-WS02-2 Tracing remains intentionally conservative

Changed-code-to-endpoint mapping currently follows direct imports and direct call sites. It does not yet model deeper indirection, wrappers, factories, dynamic imports, or broader data flow. That keeps false confidence low, but it also means endpoint impact can still be under-reported for real services with more layered call graphs.

## WS-03 Invariants, Suggestions, And Scenarios

### R-WS03-1 Mined invariant extraction can still be noisy at the policy boundary

The mined-test extractor now avoids unsupported helper tests, but it can still emit an invariant when it finds only part of the expected evidence pattern, such as request-only or response-only data. That is within the current narrow contract, but it is the next place where noisy or weak invariants can leak into later layers.

### R-WS03-2 Conflicting confirmed baselines are not resolved

Scenario building now correctly prefers confirmed baselines over suggested ones, but if the same request ends up with multiple different confirmed responses, the builder still takes the first confirmed response it sees. That leaves baseline selection ambiguous if real repos contain contradictory mined fixtures.

### R-WS03-3 Suggested invariants without request context do not become scenarios

Suggested invariants are useful only when they include request-shaped context. Suggestions without a usable request are not promoted into replay or DST scenarios yet, which limits the practical value of suggestion providers until the invariant schema grows richer.

## WS-04 Differential Replay And Property Checks

### R-WS04-1 Replay classification is still heuristic

Differential replay is now anchored to confirmed baselines, but the result classifier is still intentionally simple. It relies mostly on status-class changes plus coarse field-level response diffs, and same-rank body changes default to non-breaking classifications. That is stable enough for now, but it is not yet domain-aware.

### R-WS04-2 Property generation is conservative and schema-light

The property runner now preserves request shape better, especially for lists, but it still derives Hypothesis strategies from a single request example. That keeps generation honest, yet exploration remains narrow because there are no richer field constraints, semantic generators, or invariant-specific domains.

## WS-05 Deterministic Runtime And ASGI Harness

### R-WS05-1 DST runtime is still a contract shell, not a full execution engine

The scheduler, fault plan, and ASGI harness surfaces now exist, but the runtime still does not inject faults into real execution or track actual async yield points. That means the current DST layer is useful for interface stabilization, not yet for proving deterministic concurrency behavior under faulted interleavings.

### R-WS05-2 ASGI request streaming and disconnect behavior remain simplified

The harness now avoids inventing disconnects after the request body, but it still does not model streaming request bodies, partial body delivery, or deliberate disconnect injection. Any app behavior that depends on chunked request handling or disconnect timing is still outside current coverage.

### R-WS05-3 Response parse failures are preserved only as raw text

Malformed JSON responses no longer crash the harness, which is the correct baseline behavior. However, parse failures are not surfaced as structured metadata in the trace or result model, so downstream layers cannot currently distinguish "text response" from "declared JSON but invalid body" without re-inspecting headers and payloads themselves.

## WS-06 Semantic Simulators

### R-WS06-1 Redis coverage is present but still narrow

WS-06 now has approved HTTP, SQLAlchemy, and Redis slices, so the core simulator surface exists. However, the Redis layer still does not patch `redis.asyncio`, only supports single-key `brpop`, and rejects pub/sub explicitly instead of simulating it. That means the launch external-state model is broader than before, but still not close to full client fidelity.

### R-WS06-2 HTTP adapters still cover only a narrow client surface

The HTTP simulator now honors deterministic fixtures and slow-response faults correctly, but the adapters still do not model streaming bodies, richer client APIs, or broader request features beyond the tested request path. Apps that depend on deeper `httpx` or `aiohttp` behavior can still fall outside the simulator contract.

### R-WS06-3 SQLAlchemy semantics are intentionally narrower than real async SQLAlchemy

The SQLAlchemy simulator now has better read-committed visibility and non-conflicting commit merging, but it still does not patch `sqlalchemy.ext.asyncio`, introspect real ORM metadata, or model joins, deadlocks, commit-time timeouts, or richer query behavior. It remains a focused state machine, not a drop-in ORM substitute.

### R-WS06-4 Conflicting concurrent writes are still last-write-wins

The SQLAlchemy slice now avoids losing non-conflicting commits, but concurrent writes to the same logical row are still resolved by commit order rather than lock, conflict, or deadlock semantics. That is acceptable for this checkpoint, but it leaves important real-database failure modes outside current coverage.

### R-WS06-5 Redis fault and queue semantics are still intentionally shallow

The Redis simulator now handles strings, hashes, lists, expiry, blocking single-key `brpop`, and several explicit fault modes, but it still omits richer Redis behavior such as multi-key blocking pops, transactions, scripts, streams, and pub/sub delivery semantics. It is a narrow semantic state machine, not a drop-in replacement for broader Redis usage.

## Cross-Workstream Risks

### R-X-1 One-repo-per-process is still an implicit system assumption

Multiple reviewed components currently rely on a short-lived CLI process model. Discovery, import loading, and replay behavior are safer under that assumption than they would be in a persistent multi-repo worker. If architecture moves toward a service process, this assumption needs to be made explicit and then removed deliberately.

### R-X-2 Verification depth is still weighted toward narrow unit slices

The current review loop has strong targeted tests for individual behaviors, but end-to-end verification of the full `discover -> invariants -> scenarios -> property/replay -> reporting` pipeline is still limited. More integration coverage will be needed before WS-07 and WS-08 can trust the composed system.

## Recommended Follow-Through

1. Add explicit ownership for each residual risk as workstreams WS-05 through WS-08 are claimed.
2. Keep confirmed and suggested behavior separated in every new layer unless a review explicitly approves a merge point.
3. Add integration tests that exercise full verification flow before watch mode and GitHub Action reporting are considered stable.
4. Revisit the property schema before expanding Hypothesis generation, so richer exploration does not outpace the trust model.
