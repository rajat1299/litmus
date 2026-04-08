# B3 Search-Budget Scaling Design

**Date:** 2026-04-07  
**Status:** slice 1 design  
**Scope:** WS-22 bounded first slice for Track B3

---

## Goal

Make Litmus search-budget behavior explicit before changing search depth.

This slice does not raise local or CI replay seed defaults. It adds the artifact contract needed to explain how the current coarse budget was allocated and spent across scenarios and targets.

---

## Problem

Litmus currently exposes:

- `fault_profile`
- `budget_policy`
- `replay_seeds_per_scenario`

That is not enough to explain actual search behavior. A user cannot tell:

- how many seeds were requested for a scenario
- whether a scenario had reachable targets at all
- whether seeds were spread across multiple reachable targets or collapsed to one
- whether a no-boundary scenario consumed the full nominal budget or a bounded placeholder run

That makes B3 unsafe to widen. If we increase search depth without this accounting, loop-time regressions and weak allocations will be hard to reason about.

---

## Slice 1 Contract

Add a Litmus-native search-budget artifact with two levels:

1. Verification-level summary
2. Per-scenario allocation snapshots persisted on replay traces

The contract should answer:

- what budget policy was requested
- how many replay seeds per scenario were requested
- how many scenarios had reachable targets
- how many scenarios collapsed to `no_boundary`
- how many unique reachable targets were seen
- how many seeds were actually allocated and executed

Per-scenario snapshots should answer:

- requested seeds
- allocated seeds
- reachable selected targets
- whether allocation was target-spread or `no_boundary`

---

## Source Of Truth

The source of truth stays Litmus-native and planner-owned:

- coarse requested budget comes from existing performance policy helpers
- per-scenario allocation comes from reachability plus planned fault-seed construction
- run summaries aggregate from the persisted search-budget snapshots rather than re-deriving from console output

Claude Code concepts are relevant only as control-plane inspiration for normalized artifact shape.

---

## Deliberate Non-Goals

This slice does not:

- raise local replay depth
- change CI replay depth
- add a new user-facing fault profile
- change scenario prioritization
- add adaptive pruning or time-sliced search execution

Those come only after the accounting artifact is reviewed.

---

## Exit Criteria

- verification artifacts persist per-scenario search-budget allocation
- run summaries expose aggregate requested versus allocated replay budget
- no-boundary collapse is visible and honest
- existing replay semantics stay unchanged
