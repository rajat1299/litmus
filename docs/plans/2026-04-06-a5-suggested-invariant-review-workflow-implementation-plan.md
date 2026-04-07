# A5 Suggested Invariant Review Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a durable, auditable review lifecycle for suggested invariants without collapsing the trust boundary between suggested and confirmed behavior.

**Architecture:** Keep invariant `status` as the trust/enforcement axis, add separate suggestion review metadata in the curated invariant store, and write accept/dismiss actions into run activity history for audit. Active verification should continue to enforce only confirmed invariants while pending suggested items remain reviewable and dismissed suggestions stay suppressed but visible in explicit review surfaces.

**Tech Stack:** Python 3.11, Typer CLI, Pydantic models, PyYAML invariant store, pytest

---

### Task 1: Add suggestion review metadata and lifecycle handling

**Files:**
- Modify: `src/litmus/invariants/models.py`
- Modify: `src/litmus/invariants/suggested.py`
- Modify: `src/litmus/dst/engine.py`
- Test: `tests/unit/invariants/test_suggested.py`
- Test: `tests/unit/dst/test_engine.py`

**Step 1: Write the failing tests**

Add tests that prove:
- suggested invariants can carry review metadata without changing `status`
- dismissed suggested invariants suppress regenerated route-gap suggestions
- dismissed suggested invariants do not appear in active verification inputs

**Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/unit/invariants/test_suggested.py tests/unit/dst/test_engine.py`
Expected: FAIL on missing review metadata / dismissal handling

**Step 3: Write minimal implementation**

Add:
- review metadata models for suggested invariants
- helpers to tell whether a suggestion is pending, dismissed, or promoted
- route-gap suggestion suppression based on dismissed suggested records
- active verification input filtering that excludes dismissed suggested records

**Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/unit/invariants/test_suggested.py tests/unit/dst/test_engine.py`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/invariants/models.py src/litmus/invariants/suggested.py src/litmus/dst/engine.py tests/unit/invariants/test_suggested.py tests/unit/dst/test_engine.py
git commit -m "feat: add suggested invariant review state"
```

### Task 2: Add bounded CLI review workflow and curated store updates

**Files:**
- Modify: `src/litmus/management.py`
- Modify: `src/litmus/cli.py`
- Modify: `src/litmus/surface.py`
- Test: `tests/integration/test_management_commands.py`
- Test: `tests/unit/test_package_surfaces.py`

**Step 1: Write the failing tests**

Add tests for:
- `litmus invariants review list` defaulting to pending items
- `litmus invariants accept <name>` promoting a suggested invariant while preserving provenance
- `litmus invariants dismiss <name> --reason ...` recording dismissal metadata in `.litmus/invariants.yaml`
- `litmus invariants show <name>` surfacing review metadata

**Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/integration/test_management_commands.py tests/unit/test_package_surfaces.py`
Expected: FAIL on missing commands / output

**Step 3: Write minimal implementation**

Add:
- management-layer review actions and result models
- bounded CLI commands for review list, accept, and dismiss
- updated invariant detail rendering and surface contract entries

**Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/integration/test_management_commands.py tests/unit/test_package_surfaces.py`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/management.py src/litmus/cli.py src/litmus/surface.py tests/integration/test_management_commands.py tests/unit/test_package_surfaces.py
git commit -m "feat: add invariant review commands"
```

### Task 3: Persist review audit history and surface pending review state in reports/MCP

**Files:**
- Modify: `src/litmus/runs/models.py`
- Modify: `src/litmus/runs/store.py`
- Modify: `src/litmus/mcp/types.py`
- Modify: `src/litmus/mcp/tools.py`
- Modify: `src/litmus/reporting/console.py`
- Modify: `src/litmus/reporting/pr_comment.py`
- Test: `tests/unit/reporting/test_console.py`
- Test: `tests/unit/reporting/test_pr_comment.py`
- Test: `tests/unit/runs/test_summary.py`

**Step 1: Write the failing tests**

Add tests that prove:
- review actions are stored as run activities
- CLI/MCP/reporting surfaces show pending review items clearly
- dismissed suggestions are hidden from default review summaries

**Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/unit/reporting/test_console.py tests/unit/reporting/test_pr_comment.py tests/unit/runs/test_summary.py`
Expected: FAIL on missing activity type / review payloads

**Step 3: Write minimal implementation**

Add:
- invariant-review activity records in run history
- MCP-friendly review payloads
- pending-review reporting updates in CLI and PR comments

**Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/unit/reporting/test_console.py tests/unit/reporting/test_pr_comment.py tests/unit/runs/test_summary.py`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/runs/models.py src/litmus/runs/store.py src/litmus/mcp/types.py src/litmus/mcp/tools.py src/litmus/reporting/console.py src/litmus/reporting/pr_comment.py tests/unit/reporting/test_console.py tests/unit/reporting/test_pr_comment.py tests/unit/runs/test_summary.py
git commit -m "feat: audit invariant review actions"
```
