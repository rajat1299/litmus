# Litmus Next-Phase Action Items

**Status Date:** 2026-04-05  
**Scope:** Post-WS-17 execution map for launch closeout, deeper moat work, and platform/product expansion  
**Primary References:** `product/STATUS.md`, `docs/reviews/2026-03-30-residual-risks.md`, `docs/reviews/2026-03-31-spec-coverage-matrix.md`, `product/litmus-product-spec.md`, `README.md`, and `claudecode/`

---

## Purpose

This document answers one practical question for the team:

What are the next meaningful action items after WS-17, what does each item actually require, and where should Litmus borrow or adapt Claude Code engineering instead of inventing everything from scratch?

This is not a single implementation plan. It is a post-tranche execution map that separates:

- public-alpha closeout work
- next moat-deepening work
- later platform/product expansion

The team should use this doc to decide what to staff next, what can run in parallel, and which Claude Code primitives are safe foundations versus references only.

## Current Position

Litmus has now landed the core tranche-one platform and three moat-deepening slices:

- WS-15: cross-layer DST in shipped `verify`
- WS-16: exact replay fidelity via persisted execution transcripts
- WS-17: fault-path reachability and target-aware local coverage

That means the product is no longer missing its spine. The remaining work is now split between:

1. making the shipped product public-alpha clean
2. deepening the verification moat beyond the current bounded runtime model
3. building the platform/product surfaces that sit around the moat

## Core Planning Rule

Claude Code should be used as a source of **control-plane engineering** and **platform primitives**, not as a source of Litmus's verification engine.

Borrow heavily for:

- run/session/task lifecycle
- MCP and structured tool contracts
- event and artifact pipelines
- extension and plugin loading
- remote session coordination
- session history and audit trails

Do not transplant for:

- deterministic runtime algorithms
- scheduler/search behavior
- simulator semantics
- invariant reasoning or verification logic
- Anthropic-specific UI shell, API, bridge, or analytics systems

## Claude Code Borrowing Map

### Safe Foundation To Borrow

- [Task.ts](/Users/rajattiwari/litmus/claudecode/Task.ts)
- [AppStateStore.ts](/Users/rajattiwari/litmus/claudecode/state/AppStateStore.ts)
- [Tool.ts](/Users/rajattiwari/litmus/claudecode/Tool.ts)
- [tools.ts](/Users/rajattiwari/litmus/claudecode/tools.ts)
- [entrypoints/mcp.ts](/Users/rajattiwari/litmus/claudecode/entrypoints/mcp.ts)
- [QueryEngine.ts](/Users/rajattiwari/litmus/claudecode/QueryEngine.ts)
- [query.ts](/Users/rajattiwari/litmus/claudecode/query.ts)
- [skills/loadSkillsDir.ts](/Users/rajattiwari/litmus/claudecode/skills/loadSkillsDir.ts)
- [loadPluginCommands.ts](/Users/rajattiwari/litmus/claudecode/utils/plugins/loadPluginCommands.ts)
- [RemoteSessionManager.ts](/Users/rajattiwari/litmus/claudecode/remote/RemoteSessionManager.ts)
- [sessionHistory.ts](/Users/rajattiwari/litmus/claudecode/assistant/sessionHistory.ts)
- [sessionMemory.ts](/Users/rajattiwari/litmus/claudecode/services/SessionMemory/sessionMemory.ts)

### Reference Only, Do Not Transplant

- [main.tsx](/Users/rajattiwari/litmus/claudecode/main.tsx)
- [REPL.tsx](/Users/rajattiwari/litmus/claudecode/screens/REPL.tsx)
- [services/api/claude.ts](/Users/rajattiwari/litmus/claudecode/services/api/claude.ts)
- [bridgeMain.ts](/Users/rajattiwari/litmus/claudecode/bridge/bridgeMain.ts)
- [growthbook.ts](/Users/rajattiwari/litmus/claudecode/services/analytics/growthbook.ts)

## Recommended Execution Tracks

### Track A: Public Alpha Closeout

This track turns the current grounded alpha into a clean external product.

### Track B: Next Moat Depth

This track deepens Litmus's technical differentiation after WS-17.

### Track C: Expansion Platform

This track prepares the repo for adapters, hosted runs, dashboards, and new runtimes.

Track A and Track B can run in parallel if ownership is clear. Track C should begin only when Track A is stable or when a concrete staffing trigger exists.

---

## Track A: Public Alpha Closeout

### A1. Product Truth And Launch Narrative Reconciliation

**Checkpoint Status**

Implemented on 2026-04-05 as a grounded-surface reconciliation pass across alpha docs, CLI help, MCP descriptions, and reporting labels, while keeping the top-level `README.md` aspirational.

**What this item is**

Reconcile the shipped product story across grounded docs, product spec framing, alpha docs, demo flow, and in-product output so Litmus says exactly what it does today, while making the top-level `README.md` explicitly remain aspirational.

**Why this matters**

The current risk is not missing capability. It is trust drift between the shipped product and the broader aspirational narrative.

**What needs to be done**


- decide what stays aspirational in `product/litmus-product-spec.md` versus what is launch truth
- make grounded docs the source of truth for supported stack, seed depth, MCP status, and install path
- ensure CLI/MCP/reporting language matches the supported-surface story

**Borrow / adapt from Claude Code**

- Adapt the typed command/tool metadata mindset from [Tool.ts](/Users/rajattiwari/litmus/claudecode/Tool.ts) and [tools.ts](/Users/rajattiwari/litmus/claudecode/tools.ts) so user-facing operations have a single contract surface.
- Adapt the session/result normalization discipline from [QueryEngine.ts](/Users/rajattiwari/litmus/claudecode/QueryEngine.ts) so README claims and actual result envelopes stay coupled.

**What stays Litmus-native**

- support matrix
- verification claims
- zero-config contract language
- failure explanation language

**How to integrate it**

- treat Litmus command/result schemas as the canonical user-facing API
- use those schemas to drive docs, MCP output, and CLI wording
- do not add a Claude Code-style command shell or slash-command layer

**Exit criteria**

- grounded public docs no longer over-claim or under-claim current shipped behavior
- alpha quickstart, release notes, spec framing, CLI help, reporting labels, and MCP surfaces tell the same shipped story
- the top-level `README.md` is explicitly treated as aspirational rather than as launch-truth copy

### A2. Distribution And Install Automation

**What this item is**

Turn the local packaging proof into a repeatable publish path and make an explicit decision on Homebrew.

**Why this matters**

A strong CLI product still fails external adoption if install and release paths are manual or ambiguous.

**What needs to be done**

- automate package build and publish flow
- harden versioning and release metadata
- decide whether Homebrew is first-wave launch scope or explicitly deferred
- ensure install docs match supported Python/runtime requirements

**Borrow / adapt from Claude Code**

- Adapt the operational discipline around command metadata and lifecycle from [commands.ts](/Users/rajattiwari/litmus/claudecode/commands.ts) and [Task.ts](/Users/rajattiwari/litmus/claudecode/Task.ts) for release tasks, state transitions, and failure visibility.

**What stays Litmus-native**

- Python packaging
- release channels
- version policy

**How to integrate it**

- keep release automation inside Litmus's existing Python/GitHub Action toolchain
- use Claude Code patterns only for status modeling and artifact/report structure

**Exit criteria**

- a repeatable release path exists
- install docs are honest
- package version drift risk is materially reduced

### A3. Compatibility Matrix And Honest Degradation Harness

**What this item is**

Formalize the supported launch stack as a tested compatibility matrix and strengthen the unsupported-path story.

**Why this matters**

The zero-config claim only holds if supported versions and unsupported cases are explicit and tested.

**What needs to be done**

- define supported library/version matrix for FastAPI/Starlette, `httpx`, SQLAlchemy async, Redis async
- add compatibility fixtures against that matrix
- strengthen capability reporting when patching/interception cannot happen
- make unsupported coverage visible in CLI, replay, PR comments, and MCP

**Borrow / adapt from Claude Code**

- Borrow result-shape discipline from [entrypoints/mcp.ts](/Users/rajattiwari/litmus/claudecode/entrypoints/mcp.ts) and [QueryEngine.ts](/Users/rajattiwari/litmus/claudecode/QueryEngine.ts) for structured reporting.
- Adapt permission/capability explanation patterns from Claude Code's permission/result UI logic conceptually, but not the UI code itself.

**What stays Litmus-native**

- boundary coverage model
- unsupported-stack taxonomy
- simulator support decisions

**How to integrate it**

- extend Litmus run artifacts with a clear compatibility/capability section
- do not rely on free-text console summaries as the sole source of truth

**Exit criteria**

- supported versions are explicit
- unsupported scenarios degrade honestly and consistently
- compatibility drift becomes test-visible

### A4. CLI Management Surface: Invariants, Config, Fault Profiles

**What this item is**

Add the missing operator-facing CLI surface described in the README/spec: invariant management, config setting, and user-visible fault-profile selection.

**Why this matters**

The core engine is ahead of the user-facing management surface. That creates friction for real use.

**What needs to be done**

- add `litmus invariants list`
- add `litmus invariants edit` or a narrower first-wave equivalent
- add `litmus config set ...`
- expose user-facing fault profile controls with honest defaults

**Borrow / adapt from Claude Code**

- Borrow command metadata and schema patterns from [types/command.ts](/Users/rajattiwari/litmus/claudecode/types/command.ts), [commands.ts](/Users/rajattiwari/litmus/claudecode/commands.ts), and [Tool.ts](/Users/rajattiwari/litmus/claudecode/Tool.ts).
- Adapt only minimal shared operation models where CLI and MCP genuinely need the same boundary.

**What stays Litmus-native**

- config schema
- invariant file format
- fault profile semantics

**How to integrate it**

- keep Typer as the CLI surface
- extract shared request/response models only where MCP and CLI overlap
- do not introduce a generic command registry unless real duplication appears

**Exit criteria**

- README/spec management commands are either implemented or explicitly removed from launch claims
- invariant and config operations have stable structured outputs

### A5. Suggested Invariant Review Workflow

**What this item is**

Turn suggested invariants from visible-but-thin outputs into a true reviewable lifecycle.

**Why this matters**

Litmus's trust model depends on keeping confirmed versus suggested behavior clearly separated while still making suggestion review useful.

**What needs to be done**

- define suggestion states and promotion path
- improve provenance and rationale storage
- add accept/dismiss/promote workflow
- make review state visible in CLI, replay, PR comments, and MCP

**Borrow / adapt from Claude Code**

- Borrow audit/history patterns from [sessionHistory.ts](/Users/rajattiwari/litmus/claudecode/assistant/sessionHistory.ts) and [sessionMemory.ts](/Users/rajattiwari/litmus/claudecode/services/SessionMemory/sessionMemory.ts).
- Adapt result/event normalization from [QueryEngine.ts](/Users/rajattiwari/litmus/claudecode/QueryEngine.ts) for suggestion provenance and review actions.

**What stays Litmus-native**

- invariant schema
- suggestion policy
- enforcement model

**How to integrate it**

- store suggestion actions as Litmus artifact history, not ad hoc CLI state
- keep confirmed invariants as the only enforced baseline unless explicitly promoted

**Exit criteria**

- suggestions are reviewable, promotable, and auditable
- the trust boundary between confirmed and suggested remains intact

### A6. Performance And Launch SLO Hardening

**What this item is**

Establish performance budgets and verify the product against its under-10-second narrative on representative launch fixtures.

**Why this matters**

Speed is part of the product contract, not just an implementation detail.

**What needs to be done**

- define local and CI performance budgets
- add benchmark/smoke checks for core flows
- tune replay, DST, and reporting overhead where needed
- identify which deeper search budgets are safe for default launch behavior

**Borrow / adapt from Claude Code**

- Adapt task/result lifecycle instrumentation ideas from [Task.ts](/Users/rajattiwari/litmus/claudecode/Task.ts) and [QueryEngine.ts](/Users/rajattiwari/litmus/claudecode/QueryEngine.ts) for timing, budget accounting, and surfaced progress.

**What stays Litmus-native**

- performance targets
- search budget policy
- verification-loop tradeoffs

**How to integrate it**

- attach timing and budget summaries to Litmus run artifacts
- do not add a generic telemetry stack or product analytics framework from Claude Code

**Exit criteria**

- Litmus has explicit performance SLOs
- the launch loop is measured rather than assumed

---

## Track B: Next Moat Depth

### B1. Multi-Fault Reachability And Failure-Only Branch Discovery

**What this item is**

Go beyond WS-17's bounded single-fault reachability so Litmus can discover branches that appear only after one injected failure reveals another dependency.

**Why this matters**

This is the clearest remaining moat gap after WS-17.

**What needs to be done**

- design bounded multi-fault exploration rules
- define which combinations are worth probing locally
- record multi-step reachability artifacts cleanly
- keep local cost bounded and user-explainable

**Borrow / adapt from Claude Code**

- Adapt task orchestration and artifact sequencing from [Task.ts](/Users/rajattiwari/litmus/claudecode/Task.ts), [QueryEngine.ts](/Users/rajattiwari/litmus/claudecode/QueryEngine.ts), and [query.ts](/Users/rajattiwari/litmus/claudecode/query.ts).

**What stays Litmus-native**

- probe algorithm
- fault-combination strategy
- search-pruning logic

**How to integrate it**

- use Claude Code patterns for state transitions, attachments, and bounded execution accounting
- keep the actual reachability/search engine entirely inside Litmus DST code

**Exit criteria**

- local planning can discover important failure-only branches beyond the clean path and single-fault probes
- cost and explanation remain bounded

### B2. Scheduler-Level Deterministic Replay

**What this item is**

Move beyond transcript comparison toward deeper deterministic execution-order replay.

**Why this matters**

WS-16 made replay more honest. This item makes replay more exact.

**What needs to be done**

- define a true execution-order replay contract
- persist the minimal runtime state necessary to reproduce ordering
- detect replay drift at the scheduler/event level
- keep the replay model understandable for users

**Borrow / adapt from Claude Code**

- Adapt event/log normalization and attachment patterns from [QueryEngine.ts](/Users/rajattiwari/litmus/claudecode/QueryEngine.ts) and [query.ts](/Users/rajattiwari/litmus/claudecode/query.ts).
- Borrow task/run lifecycle discipline from [Task.ts](/Users/rajattiwari/litmus/claudecode/Task.ts).

**What stays Litmus-native**

- runtime scheduler
- replay semantics
- event-order guarantees

**How to integrate it**

- use a Litmus-native replay transcript schema
- keep Claude Code usage limited to sequencing and artifact-shape inspiration

**Exit criteria**

- `litmus replay` is materially closer to true execution-order reproduction
- divergence is detectable and explainable at a deeper runtime level

### B3. Search-Depth Scaling And Smarter Fault Budgets

**What this item is**

Raise local and CI search depth without turning the developer loop into a slow batch job.

**Why this matters**

Now that planning is more target-aware, deeper search can produce real moat value instead of wasted seeds.

**What needs to be done**

- revisit local seed defaults and CI depth
- add target-aware and scenario-aware budget allocation
- decide whether user-facing fault profiles should also control search strategy
- measure performance impact continuously

**Borrow / adapt from Claude Code**

- Adapt budget/state accounting ideas from [query/tokenBudget.ts](/Users/rajattiwari/litmus/claudecode/query/tokenBudget.ts) conceptually and [Task.ts](/Users/rajattiwari/litmus/claudecode/Task.ts) structurally.

**What stays Litmus-native**

- seed budgets
- fault scheduling policy
- scenario prioritization

**How to integrate it**

- budget accounting should live inside Litmus run artifacts and DST planning state
- avoid porting Claude Code's generic budget stack directly

**Exit criteria**

- search depth increases where it matters
- loop time remains within an explicit product budget

### B4. Broader Supported-Stack Simulator Fidelity

**What this item is**

Expand beyond the current narrow supported constructor surfaces and shallow semantic coverage.

**Why this matters**

The moat remains real but narrow until more common client shapes and library behaviors are supported.

**What needs to be done**

- prioritize next library patterns by real user value
- deepen HTTP, SQLAlchemy, and Redis semantics incrementally
- expand monkeypatch coverage carefully
- keep honest degradation ahead of surface expansion

**Borrow / adapt from Claude Code**

- Borrow almost nothing from Claude Code for the simulation logic itself.
- Use Claude Code only for structured capability reporting and artifact shaping.

**What stays Litmus-native**

- almost all of this item

**How to integrate it**

- keep simulator design fully inside `src/litmus/simulators/`
- use shared run/report artifacts to expose broader fidelity, not to define it

**Exit criteria**

- the supported launch stack is meaningfully broader and better tested
- unsupported cases remain explicit

---

## Track C: Expansion Platform

### C1. Adapter And Plugin Architecture

**What this item is**

Create the extension system that can support new framework packs, simulator packs, and org-specific verification logic.

**Why this matters**

This is the cleanest path to broader stack support without bloating the core.

**What needs to be done**

- define adapter/plugin boundaries
- specify packaging and loading rules
- decide what a framework pack or simulator pack can contribute
- keep core verification contracts stable underneath extensions

**Borrow / adapt from Claude Code**

- Borrow heavily from [skills/loadSkillsDir.ts](/Users/rajattiwari/litmus/claudecode/skills/loadSkillsDir.ts) and [loadPluginCommands.ts](/Users/rajattiwari/litmus/claudecode/utils/plugins/loadPluginCommands.ts).

**What stays Litmus-native**

- adapter APIs
- simulator/provider contracts
- verification execution model

**How to integrate it**

- use Claude Code's discovery/loading pattern, namespace handling, and plugin manifest thinking
- do not mirror the full Claude Code plugin marketplace or UI system

**Exit criteria**

- a second adapter family or simulator pack can be added without reshaping the core

### C2. Hosted Runs And Remote Verification Sessions

**What this item is**

Build the control plane for remote verification workers, live run streaming, and reconnectable hosted sessions.

**Why this matters**

This is the bridge from solo CLI adoption to team product and hosted monetization.

**What needs to be done**

- define remote run lifecycle
- define event streaming and artifact upload/download
- handle approvals, reconnects, and cancellation
- align remote results with local run artifacts

**Borrow / adapt from Claude Code**

- Borrow heavily from [RemoteSessionManager.ts](/Users/rajattiwari/litmus/claudecode/remote/RemoteSessionManager.ts), [Task.ts](/Users/rajattiwari/litmus/claudecode/Task.ts), and [AppStateStore.ts](/Users/rajattiwari/litmus/claudecode/state/AppStateStore.ts).

**What stays Litmus-native**

- verification job model
- artifact schema
- security/runtime isolation choices

**How to integrate it**

- treat local and remote runs as the same Litmus artifact family
- use Claude Code only for remote control-plane patterns and session lifecycle

**Exit criteria**

- remote verification can be introduced without redesigning the run model

### C3. Team History, Dashboard, And Observability Surfaces

**What this item is**

Turn run artifacts into durable team-facing product surfaces: session history, confidence trends, policy controls, and observability integrations.

**Why this matters**

This is the natural team-facing layer after PR comments stop being enough.

**What needs to be done**

- define durable run history APIs
- design trend and comparison surfaces
- define policy and threshold controls
- design observability export/integration model

**Borrow / adapt from Claude Code**

- Borrow history/state concepts from [sessionHistory.ts](/Users/rajattiwari/litmus/claudecode/assistant/sessionHistory.ts), [sessionMemory.ts](/Users/rajattiwari/litmus/claudecode/services/SessionMemory/sessionMemory.ts), [AppStateStore.ts](/Users/rajattiwari/litmus/claudecode/state/AppStateStore.ts), and [QueryEngine.ts](/Users/rajattiwari/litmus/claudecode/QueryEngine.ts).

**What stays Litmus-native**

- confidence model
- verification analytics
- team product semantics

**How to integrate it**

- build dashboard/team surfaces directly off Litmus run and artifact records
- do not build a Claude Code-style chat product around them

**Exit criteria**

- run history and trends are first-class product assets, not just local files

### C4. TypeScript / Node Fast-Follow

**What this item is**

Add a second runtime family without destabilizing the Python-first launch product.

**Why this matters**

This is the biggest expansion opportunity, but also the easiest place to overreach.

**What needs to be done**

- define Node runtime support boundaries
- map equivalent external-state model (`fetch`, Prisma/pg, Redis)
- decide how much of the Python artifact model can remain shared
- build a narrow launch adapter family before broadening further

**Borrow / adapt from Claude Code**

- Borrow the extension-system approach from [skills/loadSkillsDir.ts](/Users/rajattiwari/litmus/claudecode/skills/loadSkillsDir.ts) and [loadPluginCommands.ts](/Users/rajattiwari/litmus/claudecode/utils/plugins/loadPluginCommands.ts).
- Borrow remote/session modeling patterns from [Task.ts](/Users/rajattiwari/litmus/claudecode/Task.ts) and [RemoteSessionManager.ts](/Users/rajattiwari/litmus/claudecode/remote/RemoteSessionManager.ts) if multi-runtime hosted execution appears.

**What stays Litmus-native**

- Node simulator semantics
- runtime strategy
- verification core

**How to integrate it**

- keep Python and Node sharing artifact contracts where useful
- keep simulator/runtime implementations runtime-native

**Exit criteria**

- a narrow Node launch path exists without damaging the Python-first core

---

## Recommended Order

### Immediate

1. A1 Product truth and launch narrative reconciliation
2. A2 Distribution and install automation
3. A3 Compatibility matrix and honest degradation harness

### Near-Term

4. A4 CLI management surface
5. A5 Suggested invariant review workflow
6. A6 Performance and launch SLO hardening

### Next Moat

7. B1 Multi-fault reachability and failure-only branch discovery
8. B2 Scheduler-level deterministic replay
9. B3 Search-depth scaling and smarter fault budgets
10. B4 Broader supported-stack simulator fidelity

### Later Expansion

11. C1 Adapter and plugin architecture
12. C2 Hosted runs and remote verification sessions
13. C3 Team history, dashboard, and observability surfaces
14. C4 TypeScript / Node fast-follow

## Staffing Recommendation

- Assign one owner to Track A as the launch-quality owner.
- Assign one owner to Track B as the moat owner.
- Do not start Track C as open-ended platform work. Start only when a concrete product trigger exists:
  - second adapter family
  - hosted run initiative
  - dashboard/team SKU work
  - TypeScript staffing

## Final Rule For The Team

For every next item, ask this first:

Does Claude Code help us with the **control plane** around the work, or with the **verification engine** itself?

If the answer is control plane, borrowing is likely high leverage.  
If the answer is verification engine, Litmus should stay Litmus-native by default.
