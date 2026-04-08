# B3 Search-Budget Slice 1 Implementation Plan

**Date:** 2026-04-07  
**Workstream:** WS-22  
**Branch:** `codex/b3-search-budget-slice1`

---

## Bounded Deliverable

Add explicit search-budget accounting to verification artifacts and summaries without changing search depth or replay behavior.

---

## Planned Changes

1. Add replay-trace-level budget snapshot models for requested seeds, allocated seeds, selected targets, and allocation mode.
2. Populate those snapshots during `_run_replay()` from existing reachability and planned seed data.
3. Add verification-level aggregate search-budget summary derived from replay traces.
4. Extend run serialization and targeted summary/report tests.

---

## Verification

- targeted unit tests for the new budget models and summary aggregation
- targeted DST engine tests for target-aware versus no-boundary allocation snapshots
- targeted run lifecycle or summary tests proving persisted artifact shape

---

## Review Boundary

Stop after this accounting slice is implemented, tested, and committed.

The next slice can then decide whether to:

- deepen CI search selectively
- make hostile/default profiles search-strategy-aware
- introduce scenario-aware prioritization

Follow-up landed on 2026-04-08:

- same-target replay budget now diversifies across target-specific fault kinds before rerunning identical target/kind pairs
- search-budget artifacts now expose planned fault-kind coverage so repeated seeds are explainable in CLI, run summaries, and MCP payloads
