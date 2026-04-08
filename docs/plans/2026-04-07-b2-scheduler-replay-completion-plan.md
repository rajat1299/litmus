# B2 Scheduler Replay Completion Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete B2 by extending scheduler-level replay from execution-time fault decisions to the pre-execution planner decisions Litmus also owns: target selection, probe sequencing, and planned seed selection.

**Architecture:** Keep the bounded hybrid contract from slice 1. Extend the scheduler ledger with target-selection and probe decisions derived from `TargetSelectionArtifact`, recompute those planner decisions during replay against the current app, and compare them before the execution-driven part of the ledger. Continue to drive the actual replay run from the recorded ledger and fault plan, not from speculative current planning.

**Tech Stack:** Python 3.11+, dataclasses, pytest, Litmus DST reachability/replay/runtime modules.

---

### Task 1: Add planner-decision regression tests

**Files:**
- Modify: `tests/unit/replay/test_fidelity.py`
- Modify: `tests/integration/test_replay_command.py`

**Step 1: Write the failing tests**

Add tests that prove:

- scheduler ledger normalization includes probe and target-selection decisions from `TargetSelectionArtifact`
- replay reports `decision_mismatch` when the current app's target-selection planner no longer matches the recorded run even before the response drifts

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/integration/test_replay_command.py -q`
Expected: FAIL because replay does not yet compare current planner decisions.

### Task 2: Implement planner-decision ledger coverage and replay preflight comparison

**Files:**
- Modify: `src/litmus/replay/fidelity.py`
- Modify: `src/litmus/mcp/tools.py`
- Modify: `src/litmus/dst/engine.py`

**Step 1: Write minimal implementation**

- extend the scheduler ledger to include probe phases, discovered targets, selected-target summaries, and planned seed selection
- recompute current target-selection artifacts during replay
- compare those planner decisions before the execution-time ledger segment

**Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/integration/test_replay_command.py -q`
Expected: PASS.

### Task 3: Verify B2 completion and update status

**Files:**
- Modify: `product/STATUS.md`

**Step 1: Run bounded verification**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/unit/replay/test_replay_trace.py tests/unit/runs/test_run_models.py tests/integration/test_run_lifecycle.py tests/integration/test_replay_command.py tests/unit/mcp/test_tools.py tests/unit/replay/test_explain.py tests/unit/reporting/test_explanations.py tests/unit/replay/test_replay_models.py -q`
Expected: targeted B2 verification stays green.

**Step 2: Update status**

If green, mark WS-21 done and record that B2 now covers planner plus execution scheduler decisions within the bounded hybrid contract.

**Step 3: Commit**

```bash
git add product/STATUS.md docs/plans/2026-04-07-b2-scheduler-replay-completion-plan.md src/litmus/replay/fidelity.py src/litmus/mcp/tools.py src/litmus/dst/engine.py tests/unit/replay/test_fidelity.py tests/integration/test_replay_command.py
git commit -m "feat: complete scheduler replay planning coverage"
```
