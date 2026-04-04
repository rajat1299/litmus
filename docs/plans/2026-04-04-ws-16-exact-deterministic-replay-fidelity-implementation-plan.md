# WS-16 Exact Deterministic Replay Fidelity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `litmus replay <seed>` verify execution fidelity against the originally recorded failure path, not just rerun the stored request and fault plan.

**Architecture:** Keep the current replay runner and raw `TraceEvent` artifact shape, but derive and persist a normalized execution transcript per replay seed. At replay time, compare the recorded and replay transcripts, classify fidelity as `matched`, `drifted`, or `not_checked`, and surface the first divergence in CLI, MCP, and run artifacts.

**Tech Stack:** Python, dataclasses, existing `TraceEvent` runtime artifacts, Litmus replay/differential pipeline, pytest

---

### Task 1: Add Failing Fidelity Tests

**Files:**
- Create: `/Users/rajattiwari/litmus/tests/unit/replay/test_fidelity.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/replay/test_explain.py`
- Modify: `/Users/rajattiwari/litmus/tests/integration/test_replay_command.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/mcp/test_tools.py`

**Step 1: Write the failing unit tests**

Add unit tests that prove:

- a recorded trace can be normalized into an ordered execution transcript
- a replay transcript that matches is reported as `matched`
- a replay transcript with a first differing checkpoint is reported as `drifted`
- a replay record without a stored transcript reports `not_checked`

**Step 2: Write the failing integration tests**

Add integration coverage that proves:

- `litmus replay <seed>` prints execution fidelity
- MCP replay/explain results include structured fidelity data
- a replay can drift even when the response diff alone is not enough context

**Step 3: Run tests to confirm the red state**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/unit/replay/test_explain.py tests/integration/test_replay_command.py tests/unit/mcp/test_tools.py -q`

Expected: FAIL on missing fidelity types, transcript derivation, and output surfaces.

### Task 2: Add A Replay Fidelity Model

**Files:**
- Modify: `/Users/rajattiwari/litmus/src/litmus/replay/models.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/mcp/types.py`

**Step 1: Add the minimal dataclasses**

Add explicit replay-fidelity structures, for example:

- `ReplayFidelityStatus`
- `ReplayCheckpoint`
- `ReplayFidelityResult`

The model must represent:

- `matched`
- `drifted`
- `not_checked`
- first divergence details for the drift case

**Step 2: Add serialization support**

Ensure fidelity data can be carried through:

- `ReplayExplanation.to_dict()`
- `ReplayExplanation.from_dict()`
- MCP payload serialization

**Step 3: Run focused model tests**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/unit/mcp/test_tools.py -q`

Expected: model-level tests move toward green.

### Task 3: Build Transcript Normalization And Comparison

**Files:**
- Create: `/Users/rajattiwari/litmus/src/litmus/replay/fidelity.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/replay/trace.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/replay/test_fidelity.py`

**Step 1: Implement transcript normalization**

Add a focused helper that converts a `list[TraceEvent]` into a stable ordered checkpoint list.

Keep the first version intentionally narrow:

- `fault_plan_selected`
- `boundary_intercepted`
- `boundary_simulated`
- `fault_injected`
- `default_response_used`
- `app_exception`
- final response checkpoint

Ignore noisy metadata that is not needed for deterministic comparison.

**Step 2: Implement comparison**

Add a helper that compares recorded vs replay checkpoint lists and returns:

- `matched` when checkpoints are equivalent
- `drifted` with first-difference detail when they diverge
- `not_checked` when the recorded artifact has no transcript

**Step 3: Run focused transcript tests**

Run: `uv run pytest tests/unit/replay/test_fidelity.py -q`

Expected: transcript normalization and comparison tests pass.

### Task 4: Persist Execution Transcripts With Replay Records

**Files:**
- Modify: `/Users/rajattiwari/litmus/src/litmus/replay/trace.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/dst/engine.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/dst/test_engine.py`
- Modify: `/Users/rajattiwari/litmus/tests/integration/test_verify_command.py`

**Step 1: Extend replay record persistence**

Persist the normalized transcript alongside the raw trace inside `ReplayTraceRecord`.

Do not remove or replace the raw trace. The transcript is a derived execution artifact.

**Step 2: Keep old artifacts loadable**

Make loading tolerant of replay records that do not have transcript data.

**Step 3: Run verify-path tests**

Run: `uv run pytest tests/unit/dst/test_engine.py tests/integration/test_verify_command.py -q`

Expected: replay records written by `litmus verify` now contain execution transcript data without breaking existing artifacts.

### Task 5: Evaluate Fidelity During Replay

**Files:**
- Modify: `/Users/rajattiwari/litmus/src/litmus/mcp/tools.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/replay/explain.py`
- Modify: `/Users/rajattiwari/litmus/tests/integration/test_replay_command.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/replay/test_explain.py`

**Step 1: Compare recorded vs replay execution**

In `_execute_replay()`:

- derive the replay transcript from the new trace
- compare it against the stored transcript
- attach the fidelity result to the replay explanation

Keep the existing response-diff classification intact. Fidelity is additive, not a replacement for replay classification.

**Step 2: Render first divergence into the explanation**

Update explanation-building so the primary replay output can state:

- replay matched the recorded execution
- replay drifted at checkpoint N
- replay could not be fidelity-checked because the artifact predates WS-16

**Step 3: Run replay tests**

Run: `uv run pytest tests/unit/replay/test_explain.py tests/integration/test_replay_command.py -q`

Expected: replay explanations now include fidelity status and first-difference context.

### Task 6: Surface Fidelity In CLI And MCP

**Files:**
- Modify: `/Users/rajattiwari/litmus/src/litmus/reporting/explanations.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/mcp/types.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/mcp/tools.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/mcp/test_tools.py`

**Step 1: Update CLI rendering**

Render fidelity ahead of the raw trace list so developers immediately see whether replay matched or drifted.

**Step 2: Update MCP payloads**

Ensure replay and explain-failure operations serialize fidelity as structured data, not just formatted text.

**Step 3: Run surface tests**

Run: `uv run pytest tests/unit/mcp/test_tools.py tests/unit/replay/test_explain.py tests/integration/test_replay_command.py -q`

Expected: CLI and MCP expose the same fidelity contract.

### Task 7: Verify Backward Compatibility

**Files:**
- Modify only files already touched above

**Step 1: Add old-artifact regression coverage**

Add or extend tests that load a replay record without transcript data and confirm:

- replay still runs
- fidelity reports `not_checked`
- output remains honest and non-breaking

**Step 2: Run focused compatibility tests**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/integration/test_replay_command.py tests/unit/mcp/test_tools.py -q`

Expected: older replay artifacts degrade cleanly.

### Task 8: Verify The Whole Slice

**Files:**
- Modify only files already touched above

**Step 1: Run targeted verification**

Run: `uv run pytest tests/unit/replay/test_fidelity.py tests/unit/replay/test_explain.py tests/unit/dst/test_engine.py tests/unit/mcp/test_tools.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py -q`

Expected: PASS

**Step 2: Run broader regression verification**

Run: `uv run pytest -q`

Expected: PASS

**Step 3: Check whitespace**

Run: `git diff --check`

Expected: no output
