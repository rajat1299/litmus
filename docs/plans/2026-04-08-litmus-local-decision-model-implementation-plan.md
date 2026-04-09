# Litmus Local Decision Model Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add repo-local risk, evidence, policy, and verdict objects to Litmus verification results and persisted run summaries, then expose them through CLI, PR, MCP, and GitHub Action surfaces without introducing hosted services.

**Architecture:** Keep verification execution unchanged, derive a local decision bundle from the existing verification result, persist that bundle through the shared verification projection, and render it consistently across user-facing surfaces. Hosted control-plane work remains docs-only.

**Tech Stack:** Python dataclasses and enums, file-backed run manifests under `.litmus/runs/`, Typer CLI, GitHub Action reporting, MCP typed payloads, and unit/integration tests with pytest.

---

### Task 1: Define the local decision domain model

**Files:**
- Create: `src/litmus/decisioning.py`
- Test: `tests/unit/test_decisioning.py`

**Step 1: Write failing decision tests**

Cover:

- `safe` for supported clean runs
- `unsafe` for blocking regressions
- `needs_deeper_verification` for unsupported gaps
- `insufficient_evidence` for runs with no signals

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_decisioning.py -q`

**Step 3: Write minimal implementation**

Add local enums/dataclasses for:

- risk level
- merge recommendation
- verdict decision
- evidence summary
- risk assessment
- policy evaluation
- verification verdict
- decision bundle

Implement the bounded `evaluate_verification_result(...)` function.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_decisioning.py -q`

### Task 2: Persist the decision bundle through the shared verification projection

**Files:**
- Modify: `src/litmus/dst/engine.py`
- Modify: `src/litmus/runs/summary.py`
- Test: `tests/unit/runs/test_summary.py`

**Step 1: Write the failing projection assertions**

Extend projection tests to require:

- `evidence`
- `risk_assessment`
- `policy_evaluation`
- `verification_verdict`

inside `VerificationProjection` and `summarize_verification_result(...)`.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/runs/test_summary.py -q`

**Step 3: Write minimal implementation**

Thread the evaluated decision bundle onto `VerificationResult`, add typed projection fields, and serialize them into persisted run summaries without removing the existing counts.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/runs/test_summary.py -q`

### Task 3: Expose the decision contract in CLI and PR surfaces

**Files:**
- Modify: `src/litmus/reporting/console.py`
- Modify: `src/litmus/reporting/pr_comment.py`
- Modify: `src/litmus/github_action/report.py`
- Test: `tests/unit/reporting/test_console.py`
- Test: `tests/unit/reporting/test_pr_comment.py`
- Test: `tests/unit/github_action/test_report.py`

**Step 1: Write failing surface assertions**

Require decision-oriented rendering:

- verdict
- merge recommendation
- risk summary
- policy failures/warnings

while keeping existing evidence counts and compatibility sections.

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/reporting/test_console.py tests/unit/reporting/test_pr_comment.py tests/unit/github_action/test_report.py -q`

**Step 3: Write minimal implementation**

Render the decision bundle consistently in console, PR comment, and GitHub Action outputs. Keep the GitHub Action pass/fail output backward compatible while adding explicit decision fields.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/reporting/test_console.py tests/unit/reporting/test_pr_comment.py tests/unit/github_action/test_report.py -q`

### Task 4: Expose the decision contract in MCP and verify the end-to-end local flow

**Files:**
- Modify: `src/litmus/mcp/types.py`
- Modify: `src/litmus/mcp/tools.py`
- Modify: `src/litmus/cli.py`
- Modify: `docs/alpha-quickstart.md`
- Test: `tests/unit/mcp/test_tools.py`
- Test: `tests/integration/test_verify_command.py`

**Step 1: Write failing MCP and integration assertions**

Require typed MCP payloads and local verify summaries to expose the new decision objects while keeping existing output fields usable.

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/mcp/test_tools.py tests/integration/test_verify_command.py -q`

**Step 3: Write minimal implementation**

Add typed MCP payload models for the decision bundle, thread them through `run_verify_operation(...)`, and update the grounded alpha quickstart so it stays honest about the new output shape and still states that all persistence is local.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/mcp/test_tools.py tests/integration/test_verify_command.py -q`

### Task 5: Document the future hosted control plane without scaffolding code

**Files:**
- Modify: `product/STATUS.md`
- Create: `docs/plans/2026-04-08-litmus-local-decision-model-design.md`

**Step 1: Keep status honest**

Update `product/STATUS.md` before and after implementation so the repo clearly says this slice is repo-local and the hosted plane is still future work.

**Step 2: Verify docs match implementation**

Check:

- local file-backed persistence remains the only implemented system of record
- hosted control plane is described as future work only

**Step 3: Final verification**

Run: `uv run pytest tests/unit/test_decisioning.py tests/unit/runs/test_summary.py tests/unit/reporting/test_console.py tests/unit/reporting/test_pr_comment.py tests/unit/github_action/test_report.py tests/unit/mcp/test_tools.py tests/integration/test_verify_command.py -q`
