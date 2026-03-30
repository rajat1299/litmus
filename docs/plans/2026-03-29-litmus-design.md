# Litmus Repo Design

**Date:** 2026-03-29
**Status:** Approved
**Scope:** Project operating model, documentation structure, and multi-agent execution design

---

## Goal

Turn the Litmus product spec into an execution-ready repository structure that supports parallel coding-agent work with continuous review, explicit ownership, and a single live status source.

---

## Chosen Approach

We selected the "agent operating system for the repo" model rather than a minimal doc drop or a heavy RFC/ADR system.

That means the repo must provide:

- one canonical product spec
- one live status document
- one master engineering plan
- one agent handbook
- bounded workstream packets for parallel execution

This keeps the repository legible to both humans and fresh agents while avoiding a document sprawl that becomes harder to maintain than the code.

---

## Information Architecture

### Canonical artifacts

- `product/litmus-product-spec.md`
  Source of truth for product direction, launch scope, constraints, and non-goals.
- `product/STATUS.md`
  Single live control document for phase, milestones, active workstreams, blockers, and decision log.
- `docs/plans/2026-03-29-litmus-engineering-plan.md`
  Master implementation plan for the v0.1 build.

### Execution artifacts

- `docs/agents/README.md`
  How agents should work in this repo.
- `docs/agents/workstreams/*.md`
  One bounded task packet per major engineering slice.

### Design artifact

- `docs/plans/2026-03-29-litmus-design.md`
  This document. It captures the approved repo structure and operating rules.

---

## Parallel Execution Model

The repo is optimized for parallel multi-agent execution with continuous review and evaluation.

Key rules:

1. Work is claimed through `product/STATUS.md`.
2. Each workstream should own a mostly disjoint file surface.
3. Shared interfaces must be declared in the workstream packet before implementation.
4. Every workstream ends with a verification pass and a handoff note.
5. No workstream is considered complete until status, docs, and review artifacts are updated.

This avoids the common failure mode where multiple agents work "in parallel" but collide in the same files or silently drift on shared assumptions.

---

## Review And Evaluation Loop

Each implementation cycle should follow the same loop:

1. Read the spec, status file, and assigned workstream packet.
2. Claim ownership in `product/STATUS.md`.
3. Implement only within the declared scope.
4. Run the narrowest reliable verification first, then the broader suite for that slice.
5. Produce a handoff with changed files, tests run, known gaps, and next recommended step.
6. Request independent review before merging or closing the workstream.

Review is continuous rather than deferred to the end of the product build.

---

## Why This Structure Fits Litmus

Litmus itself is a verification product. The repo operating model should reflect that:

- explicit contracts rather than implicit assumptions
- replayable status rather than conversational memory
- bounded work ownership rather than ad hoc edits
- review and evaluation built into the workflow, not added later

The doc system is therefore part of the product-development infrastructure, not project overhead.

---

## Initial Workstream Map

- WS-01 Repo and CLI foundation
- WS-02 App discovery, diff tracing, endpoint mapping
- WS-03 Invariants, scenario sourcing, LLM suggestions
- WS-04 Property checks and differential replay
- WS-05 Deterministic runtime and DST scheduler
- WS-06 Semantic simulators
- WS-07 Reporting, watch mode, GitHub Action
- WS-08 Demo app, docs, packaging, release path

These workstreams are independent enough for parallel execution after the repo foundation exists, but still align around stable interfaces and shared models.

---

## Maintenance Rules

1. Update `product/litmus-product-spec.md` only when product direction changes.
2. Update `product/STATUS.md` whenever work starts, blocks, completes, or changes owner.
3. Keep the engineering plan stable; add amendments rather than silently changing prior intent.
4. Add new workstream packets instead of overloading existing ones when scope expands materially.
5. Treat stale docs as a bug. If the code and the docs disagree, the inconsistency must be resolved immediately.

---

## Outcome

The repository now has a clear operating model:

- the spec defines truth
- the engineering plan defines sequence
- workstream packets define ownership
- the status file defines current reality

This is the minimum structure needed to let multiple coding agents build Litmus without turning the repo into an untracked conversation log.
