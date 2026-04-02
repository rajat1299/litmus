# Residual Risks Through WS-14 Reviews

**Status Date:** 2026-04-01
**Scope:** Residual risks and open limitations that still remain after the reviewed WS-01 through WS-14 checkpoints. This list excludes findings that were already fixed during review.

## Purpose

This document captures the risks that still matter after the current review loop so later work does not lose context when it moves into release hardening, post-tranche planning, and any deeper verification-platform follow-on work.

## WS-01 Repo And CLI Foundation

### R-WS01-1 Thin CLI coverage

The current smoke coverage is still shallow. The bootstrap tests validate the `litmus --help` surface, but they do not yet exercise placeholder command behavior in a meaningful way. This is acceptable for the bootstrap slice, but it leaves command wiring regressions easy to miss until `verify`, `watch`, and `replay` gain real behavior.

### R-WS01-2 Version metadata drift

Package version metadata is duplicated across packaging and module code. That is not breaking today, but it creates an avoidable drift point once release packaging and automation start depending on version correctness.

## WS-02 App Discovery, Diff Tracing, And Endpoint Mapping

### R-WS02-1 App loading now relies on module-eviction heuristics in long-lived processes

ASGI app loading now evicts repo-owned modules before import, which fixes the stale-module bug for repeated verify and MCP calls. However, this is still a heuristic tied to module origin paths and top-level namespaces, not a stronger per-repo interpreter boundary. It is good enough for the current local process model, but it remains a place to revisit if Litmus grows into a heavier long-lived worker or service.

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

## WS-07 Reporting, Verify, And Replay Workflows

### R-WS07-1 Replay artifacts are local scenario records, not full DST seed replays

`litmus replay` now works over persisted local replay records, which is a useful workflow step forward. However, the current `seed:N` identifiers are deterministic artifact IDs over replayable scenarios, not a full DST seed plus fault-schedule reproduction contract. Even after WS-11 started persisting fault-plan selection into traces, replay still does not re-execute the stored schedule. That means replay is understandable and useful, but it is not yet the deeper deterministic execution story described in the product vision.

### R-WS07-2 Workflow surfaces exist, but diagnostics and metadata are still thin

The core console reporting, `litmus verify`, `litmus replay`, `litmus watch`, GitHub Action, and PR comment surfaces now exist. However, watch and action failures still surface mostly as plain console or step-summary output rather than richer diagnostics, remediation guidance, or structured machine-readable metadata. The workflow loop is real now, but it remains intentionally thin.

## WS-08 Demo, Docs, And Alpha Release Path

### R-WS08-1 Grounded alpha docs and demo still trail the aspirational README and spec

The grounded quickstart, release notes, and payment-service demo are now honest to the product Litmus actually ships today. However, the top-level README and broader product spec still describe a wider future surface than the current alpha. That is manageable if grounded docs remain the source of truth, but the public-facing story still has drift risk until those surfaces are reconciled.

### R-WS08-2 Release packaging is validated locally, not yet automated for publication

Wheel and sdist builds now install and run correctly in a fresh environment, and the release-path smoke test proves that packaging story. However, index publication and fuller release orchestration remain manual, so release reliability still depends on operator discipline rather than automation.

## WS-09 Repository Bootstrap

### R-WS09-1 `litmus init` is a narrow bootstrap, not a full repository setup assistant

`litmus init` now repairs or writes `litmus.yaml`, initializes `.litmus/invariants.yaml`, mines simple anchors under `tests/`, and reports a concise support summary. It still does not configure richer policies, suggestions, advanced discovery modes, or a full capability matrix. That is a useful bootstrap, but it is not yet a comprehensive setup flow.

## WS-10 Scoped Verification

### R-WS10-1 Scoped verify is only as precise as conservative endpoint tracing

`litmus verify` now supports explicit paths, staged changes, named diffs, and changed-test invariant sources. However, route selection is still bounded by file and module level tracing plus direct imported-call matching. Layered indirection, wrappers, factories, dynamic imports, and broader data flow can still cause under-selection or conservative over-selection in real services.

### R-WS10-2 Empty scopes remain honest but operationally easy to misread

Empty `--staged` or `--diff` scopes now correctly produce an empty verification run instead of silently falling back to the full repo. That is the safer trust behavior, but the current UX still reports that state only through a zero-signal summary. There is not yet a clearer operator-facing explanation that no routes or invariants were selected.

## WS-11 Shipped DST Moat

### R-WS11-1 Main-path seeded fault injection currently covers outbound HTTP first

The shipped verify path now injects deterministic seeded HTTP faults and records those schedules in replay traces, which is a real moat improvement over plain replay. However, SQLAlchemy and Redis are still not patched into the main verify loop, so the shipped fault model remains HTTP-first rather than cross-layer.

### R-WS11-2 Seed depth and replay fidelity are still below the broader target

Local verify now runs multiple seeded replays per scenario, but the default remains `3` seeds rather than the larger target discussed in the product vision. Replay artifacts also still restore scenario records rather than re-executing the exact stored fault schedule. The moat path is materially more real now, but it is still a bounded first slice.

### R-WS11-3 Unknown outbound traffic still falls back to a generic synthesized upstream shape

Unknown outbound HTTP now defaults to a neutral parseable JSON response and records `http_response_defaulted` in the trace, which avoids false crashes from empty-body decoding. However, Litmus is still synthesizing a generic upstream shape in those cases rather than replaying known service semantics. That is honest and trace-visible now, but it remains a fidelity limit in the shipped moat path.

## WS-12 Run Records And Replay Artifacts

### R-WS12-1 Run storage is local and file-backed, not yet a richer history surface

Run and activity records now exist and power replay lookup, CI, and watch-mode behavior, which is the right tranche-one contract. However, the store is still a local JSON-artifact model centered on latest-run pointers. There is no richer history query surface, pruning policy, or team/session view yet.

### R-WS12-2 Replay explanations are stronger, but still bounded to response and fault context

Replay output now explains baseline, current behavior, fault context, and next steps from structured data. That is materially better than the earlier string surface, but explanations are still tied to response diffs plus trace events. They do not yet capture deeper causal lineage such as scenario provenance chains, domain-aware invariants, or richer remediation reasoning.

## WS-13 Suggested Invariants

### R-WS13-1 Suggested invariants are shipped, but they are still heuristic and curated rather than LLM-backed

Suggested route gaps and curated stored suggestions now surface in verify, run summaries, and PR comments without distorting enforcement. However, the shipped suggestion path is still heuristic plus manual curation. It is not yet the broader LLM suggestion workflow described in the product vision.

### R-WS13-2 Approval UX is still direct file editing

Suggested invariants now persist and scope correctly, but there is still no dedicated accept, dismiss, or promote workflow beyond editing `.litmus/invariants.yaml` directly. That is acceptable for the current alpha, but it leaves the human-review loop thinner than the longer-term product story.

## WS-14 MCP Surface

### R-WS14-1 MCP is local stdio only

Litmus now has an agent-native MCP surface with structured `verify`, `list_invariants`, `replay`, and `explain_failure` tools. However, it is intentionally local and stdio-only. There are no resources, prompts, remote transports, auth concerns, or broader server-management contracts in this slice.

### R-WS14-2 MCP inherits the local engine’s cost and result shape

The MCP server correctly exposes structured results over the existing run and replay artifacts, which is the right narrow contract. It still calls into the same local verification engine, though, so tool latency, simulator fidelity, and scoped-verify precision are the same as the CLI’s. MCP is now agent-native, not a deeper execution plane.

## Cross-Workstream Risks

### R-X-1 Long-lived process safety is improved, but still not a hard isolation model

The reviewed slices now support repeated in-process verification and MCP calls more safely than before, especially around app module loading and replay artifact lookup. Even so, the system still assumes a simple local-process model rather than a hardened long-lived multi-tenant runtime. If Litmus moves toward a service or worker architecture, that assumption should be re-evaluated explicitly.

### R-X-2 Verification depth is still weighted toward narrow unit slices

The current review loop has strong targeted tests for individual behaviors, but end-to-end verification of the full `discover -> invariants -> scenarios -> property/replay -> reporting` pipeline is still limited. More integration coverage will be needed before WS-07 and WS-08 can trust the composed system.

## Recommended Follow-Through

1. Decide whether release hardening is now the primary next tranche, or whether deeper moat work should start immediately with a new bounded plan.
2. Keep confirmed and suggested behavior separated in every new layer unless a review explicitly approves a merge point.
3. Add more full-flow integration coverage across scoped verify, seeded HTTP fault injection, replay, MCP, and GitHub workflow reporting before those paths are considered fully stable.
4. Revisit the property schema before expanding Hypothesis generation, so richer exploration does not outpace the trust model.
5. If moat work continues next, choose the next depth increase explicitly: higher local seed budgets, richer replay fidelity, and whether SQLAlchemy or Redis patching should land in the shipped verify path.
