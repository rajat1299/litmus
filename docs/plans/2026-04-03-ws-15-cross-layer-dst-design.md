# WS-15 Cross-Layer DST In Shipped Verify Design

## Goal

Deepen the shipped `litmus verify` moat from HTTP-only DST into a zero-config cross-layer DST loop that can exercise a narrow, explicitly supported SQLAlchemy async and Redis async surface with honest degradation when Litmus cannot intercept a boundary.

## Product Decision

This slice keeps the existing public contract:

- zero-config on the supported stack
- no SDK
- no imports
- no decorators
- no silent confidence when a boundary is not actually intercepted

The engineering shape for this slice is:

- zero-config monkeypatching for a narrow supported SQLAlchemy/Redis async surface
- boundary-level coverage recording for every verify run
- shared trace/explanation/reporting primitives so CLI, replay, MCP, PR comment, and GitHub Action inherit the richer DST story automatically

## Supported First Slice

### SQLAlchemy

Support only a narrow async construction path:

- `sqlalchemy.ext.asyncio.create_async_engine(...)`
- `sqlalchemy.ext.asyncio.async_sessionmaker(...)`

Litmus will monkeypatch these entry points during app import and app execution inside the ASGI harness. If interception succeeds, Litmus will substitute simulator-backed engine/session objects tied to the active `FaultPlan`.

Not in scope for this tranche:

- sync SQLAlchemy
- arbitrary ORM query translation
- custom wrappers that bypass patched async constructors
- full metadata introspection or full SQL compatibility

### Redis

Support only a narrow async construction path:

- `redis.asyncio.Redis(...)`
- `redis.asyncio.from_url(...)`

Litmus will monkeypatch these constructors in the same runtime window and return simulator-backed clients wired to the active `FaultPlan`.

Not in scope for this tranche:

- unsupported client wrappers
- pub/sub fidelity beyond the existing simulator surface
- non-async redis clients

## Architecture

### 1. Boundary runtime context

Extend the runtime surface from “fault plan + trace” into “fault plan + trace + boundary coverage state”.

For each boundary (`http`, `sqlalchemy`, `redis`), record:

- `detected`
- `intercepted`
- `simulated`
- `faulted`
- `unsupported`

This data should be available both as trace events and as structured summary data for reporting.

### 2. ASGI harness-owned monkeypatching

The zero-config monkeypatch contract belongs in the harness, not in user code.

`src/litmus/dst/asgi.py` should:

- create the runtime context for the seed/fault plan
- install HTTP, SQLAlchemy, and Redis monkeypatches before importing or executing app code
- expose simulator-backed objects bound to that runtime
- tear patches down after execution

The same harness contract should be reused for replay so `litmus replay seed:X` re-executes with the same patched boundary behavior.

### 3. Engine-owned target selection

`src/litmus/dst/engine.py` should widen the shipped verify targets from:

- `["http"]`

to:

- `["http", "sqlalchemy", "redis"]`

The engine should still remain bounded:

- local seeds stay at current counts
- no attempt at full deterministic execution ordering
- no new user-facing fault-profile CLI in this slice

### 4. Honest degradation

If an app never hits a supported constructor path, Litmus must not imply that boundary was simulated.

Instead, the run should explicitly report that the boundary was:

- present but unsupported
- or not observed at all

That coverage state should flow into:

- verify summary
- replay explanation
- PR comment
- MCP verify/explain surfaces where applicable

### 5. Trace and explanation contract

The current replay explanation is HTTP-shaped. This slice needs target-aware trace events so replay can explain:

- what fault was scheduled
- which boundary it targeted
- whether the boundary was intercepted
- whether a fault actually injected
- what consequence followed

Examples:

- processor timeout triggered retry
- Redis idempotency lookup timed out
- database commit fault dropped staged writes
- SQLAlchemy boundary was detected but not intercepted, so DST coverage was partial

## Testing Strategy

### Unit

- boundary coverage bookkeeping in the runtime/engine layer
- target-aware replay explanation rendering
- fault-plan expansion to cross-layer targets

### Harness

- supported SQLAlchemy async path is intercepted with no app changes
- supported Redis async path is intercepted with no app changes
- unsupported usage records explicit partial coverage

### End-to-end

Add one demo-quality shipped-path regression using a small ASGI payment fixture:

- outbound processor request over `httpx`
- idempotency/cache path over `redis.asyncio`
- ledger/state write over supported SQLAlchemy async entry points

At least one seed should fail through the normal `litmus verify` path because of a DB or Redis fault, persist a replayable artifact, and produce a replay explanation that references the non-HTTP boundary context.

## Non-Goals

- full deterministic replay engine
- broad adapter coverage outside the declared supported subset
- user-facing configuration for fault profiles or seed counts
- TypeScript/Node support
- LLM-backed invariant or fixture expansion changes unrelated to the shipped verify path

## Risks And Guards

### Risk: overreaching into a full runtime rewrite

Guard: keep the patch layer narrowly scoped to constructor interception plus boundary coverage bookkeeping.

### Risk: false confidence

Guard: never mark SQLAlchemy/Redis DST as active unless the harness actually intercepted the supported constructor path.

### Risk: performance regression

Guard: reuse the existing lightweight in-memory simulators, keep local seed counts unchanged, and verify current HTTP-first paths remain green.
