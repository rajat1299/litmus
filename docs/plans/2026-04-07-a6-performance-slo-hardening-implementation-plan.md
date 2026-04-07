# A6 Performance And Launch SLO Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Litmus's launch-speed contract explicit and measured by attaching timing and budget summaries to the shipped verify flow before adding broader benchmark automation.

**Architecture:** Keep the first A6 slice narrow: record measured verify timing inside Litmus-native run artifacts, define explicit launch budgets for local and CI verification, and surface those budgets consistently in CLI and MCP verify results. Defer benchmark harnesses and deeper default-budget tuning to a later reviewed A6 slice.

**Tech Stack:** Python 3.11, Typer CLI, dataclass run artifacts, Pydantic MCP payloads, pytest

---

### Task 1: Add explicit verify timing and launch-budget summaries

**Files:**
- Modify: `product/STATUS.md`
- Modify: `src/litmus/dst/engine.py`
- Modify: `src/litmus/runs/summary.py`
- Modify: `src/litmus/runs/store.py`
- Modify: `src/litmus/reporting/console.py`
- Modify: `src/litmus/mcp/types.py`
- Modify: `src/litmus/mcp/tools.py`
- Test: `tests/unit/runs/test_summary.py`
- Test: `tests/unit/reporting/test_console.py`
- Test: `tests/unit/mcp/test_tools.py`
- Test: `tests/unit/runs/test_run_store.py`

**Step 1: Write the failing tests**

Add tests that prove:
- `verify` timing is measured rather than synthesized after the fact
- run summaries include explicit launch budgets and measured elapsed time
- CLI and MCP verify output surface budget state consistently

**Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/unit/runs/test_summary.py tests/unit/reporting/test_console.py tests/unit/mcp/test_tools.py tests/unit/runs/test_run_store.py`
Expected: FAIL on missing timing/budget summaries

**Step 3: Write minimal implementation**

Add:
- measured verify start/completion timestamps from the verification engine
- a Litmus-native launch-budget summary for local vs CI verify runs
- timing/budget sections in run artifact summaries, CLI summaries, and MCP verify payloads

**Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/unit/runs/test_summary.py tests/unit/reporting/test_console.py tests/unit/mcp/test_tools.py tests/unit/runs/test_run_store.py`
Expected: PASS

**Step 5: Commit**

```bash
git add product/STATUS.md src/litmus/dst/engine.py src/litmus/runs/summary.py src/litmus/runs/store.py src/litmus/reporting/console.py src/litmus/mcp/types.py src/litmus/mcp/tools.py tests/unit/runs/test_summary.py tests/unit/reporting/test_console.py tests/unit/mcp/test_tools.py tests/unit/runs/test_run_store.py docs/plans/2026-04-07-a6-performance-slo-hardening-implementation-plan.md
git commit -m "feat: add verify timing and budget summaries"
```
