# B2 Scheduler Ledger Slice 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Litmus-native scheduler decision ledger and replay checkpoint artifact, then make replay consume that ledger for the scheduler-owned decisions Litmus controls today.

**Architecture:** Extend replay artifacts at the `ReplayTraceRecord` layer with separate decision-ledger and checkpoint streams, teach replay comparison to classify drift with scheduler-aware reasons, and preserve WS-16 legacy fallback for older runs without the new artifact. Keep runtime behavior bounded to fault-planning and replay semantics Litmus already owns.

**Tech Stack:** Python 3.11+, dataclasses, Typer CLI, pytest, Litmus DST runtime/replay/run artifact modules.

---

### Task 1: Claim WS-21 and document the approved design

**Files:**
- Modify: `product/STATUS.md`
- Create: `docs/plans/2026-04-07-b2-scheduler-level-deterministic-replay-design.md`
- Create: `docs/plans/2026-04-07-b2-scheduler-ledger-slice-1-implementation-plan.md`

**Step 1: Update status and design docs**

Write the approved bounded-hybrid contract into the repo before touching engine logic.

**Step 2: Verify docs changed only in bounded scope**

Run: `git diff -- product/STATUS.md docs/plans/2026-04-07-b2-scheduler-level-deterministic-replay-design.md docs/plans/2026-04-07-b2-scheduler-ledger-slice-1-implementation-plan.md`
Expected: only WS-21 claim and B2 slice-1 design/plan content.

**Step 3: Commit**

```bash
git add product/STATUS.md docs/plans/2026-04-07-b2-scheduler-level-deterministic-replay-design.md docs/plans/2026-04-07-b2-scheduler-ledger-slice-1-implementation-plan.md
git commit -m "docs: claim ws-21 scheduler replay slice"
```

### Task 2: Add scheduler-ledger and replay-checkpoint artifact models

**Files:**
- Modify: `src/litmus/replay/models.py`
- Modify: `src/litmus/replay/trace.py`
- Modify: `tests/unit/replay/test_replay_trace.py`
- Modify: `tests/unit/runs/test_run_models.py`

**Step 1: Write the failing tests**

Add tests that prove:

- `ReplayTraceRecord` round-trips `scheduler_ledger` and `replay_checkpoints`
- legacy payloads without those fields still deserialize cleanly

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/replay/test_replay_trace.py tests/unit/runs/test_run_models.py -q`
Expected: FAIL because the new artifact fields do not exist yet.

**Step 3: Write minimal implementation**

Add explicit dataclasses and serialization helpers for the new artifact surfaces, and keep legacy compatibility.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/replay/test_replay_trace.py tests/unit/runs/test_run_models.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/litmus/replay/models.py src/litmus/replay/trace.py tests/unit/replay/test_replay_trace.py tests/unit/runs/test_run_models.py
git commit -m "feat: add scheduler replay artifacts"
```

### Task 3: Make replay consume the scheduler ledger and classify scheduler-aware drift

**Files:**
- Modify: `src/litmus/replay/fidelity.py`
- Modify: `src/litmus/replay/models.py`
- Modify: `src/litmus/replay/trace.py`
- Modify: `src/litmus/mcp/tools.py`
- Modify: `src/litmus/dst/engine.py`
- Modify: `tests/unit/replay/test_fidelity.py`
- Modify: `tests/integration/test_replay_command.py`

**Step 1: Write the failing tests**

Add tests that prove:

- replay prefers the recorded scheduler ledger over the trace-derived fault plan when present
- fidelity can distinguish `decision_mismatch`, `decision_missing`, `unexpected_decision`, `checkpoint_drift`, and `outcome_drift`
- legacy artifacts still return the honest fallback status

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/integration/test_replay_command.py -q`
Expected: FAIL because replay still derives its driving plan from the older trace path.

**Step 3: Write minimal implementation**

Teach the runtime-to-artifact path to emit the ledger/checkpoints, teach replay to consume that ledger, and compare replay using the bounded hybrid contract.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/integration/test_replay_command.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/litmus/replay/fidelity.py src/litmus/replay/models.py src/litmus/replay/trace.py src/litmus/mcp/tools.py src/litmus/dst/engine.py tests/unit/replay/test_fidelity.py tests/integration/test_replay_command.py
git commit -m "feat: drive replay from scheduler ledger"
```

### Task 4: Verify the bounded slice and stop for review

**Files:**
- Modify: `product/STATUS.md`

**Step 1: Run bounded verification**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/unit/replay/test_replay_trace.py tests/unit/runs/test_run_models.py tests/integration/test_replay_command.py -q`
Expected: targeted B2 slice passes.

**Step 2: Update status for handoff**

Add a bounded note that WS-21 slice 1 produced scheduler-ledger replay artifacts and preserved legacy fallback behavior.

**Step 3: Commit**

```bash
git add product/STATUS.md
git commit -m "docs: record ws-21 slice 1 handoff"
```
