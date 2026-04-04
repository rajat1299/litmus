# WS-15 Cross-Layer DST In Shipped Verify Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a zero-config, narrow, cross-layer DST loop in `litmus verify` that can intercept supported SQLAlchemy async and Redis async boundaries, record honest coverage, persist replayable artifacts, and explain DB/Redis failure context.

**Architecture:** Extend the runtime from HTTP-only DST into a boundary-aware harness. The ASGI harness owns narrow monkeypatching for supported SQLAlchemy/Redis async constructors, the engine expands scheduled fault targets, and replay/reporting surfaces consume shared boundary coverage and target-aware trace events.

**Tech Stack:** Python, ASGI harness, monkeypatch-based adapter interception, existing Litmus semantic simulators, pytest

---

### Task 1: Add Failing Runtime And Explanation Tests

**Files:**
- Modify: `/Users/rajattiwari/litmus/tests/unit/dst/test_engine.py`
- Modify: `/Users/rajattiwari/litmus/tests/integration/dst/test_asgi_harness.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/replay/test_explain.py`
- Modify: `/Users/rajattiwari/litmus/tests/integration/test_verify_command.py`
- Modify: `/Users/rajattiwari/litmus/tests/integration/test_replay_command.py`

**Step 1: Write the failing tests**

Add tests that prove:

- fault plans in shipped verify include `sqlalchemy` and `redis`
- supported SQLAlchemy/Redis constructors are intercepted with no app changes
- unsupported patterns report partial coverage explicitly
- replay explanation renders DB/Redis target context
- one end-to-end `litmus verify` failure occurs because of a DB or Redis fault

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/dst/test_engine.py tests/integration/dst/test_asgi_harness.py tests/unit/replay/test_explain.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py -q`

Expected: FAIL on missing cross-layer coverage/interception behavior.

**Step 3: Commit**

Do not commit yet. Continue once the red state is confirmed.

### Task 2: Add Boundary Coverage And Target-Aware Trace Primitives

**Files:**
- Modify: `/Users/rajattiwari/litmus/src/litmus/dst/runtime.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/replay/trace.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/replay/models.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/replay/explain.py`

**Step 1: Write minimal implementation**

Add structured boundary coverage bookkeeping and target-aware trace metadata that can represent:

- boundary detected
- boundary intercepted
- simulator active
- fault injected
- unsupported passthrough

**Step 2: Run focused tests**

Run: `uv run pytest tests/unit/replay/test_explain.py tests/unit/dst/test_engine.py -q`

Expected: previously failing coverage/explanation tests move toward green.

### Task 3: Add Narrow SQLAlchemy/Redis Monkeypatch Layer

**Files:**
- Create: `/Users/rajattiwari/litmus/src/litmus/simulators/boundary_patches.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/dst/asgi.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/discovery/app.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/simulators/sqlalchemy_async.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/simulators/redis_async.py`

**Step 1: Implement the narrow interception contract**

Patch only the supported constructor paths:

- `sqlalchemy.ext.asyncio.create_async_engine`
- `sqlalchemy.ext.asyncio.async_sessionmaker`
- `redis.asyncio.Redis`
- `redis.asyncio.from_url`

Tie created simulator objects to the active runtime/fault plan and emit boundary coverage events.

**Step 2: Run harness tests**

Run: `uv run pytest tests/integration/dst/test_asgi_harness.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`

Expected: supported interception passes and simulator regressions stay green.

### Task 4: Expand The Shipped Engine To Schedule Cross-Layer Faults

**Files:**
- Modify: `/Users/rajattiwari/litmus/src/litmus/dst/engine.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/dst/faults.py`

**Step 1: Implement minimal engine changes**

Expand the shipped verify targets from HTTP-only to:

- `http`
- `sqlalchemy`
- `redis`

Keep existing seed counts and bounded fault-plan semantics.

**Step 2: Run focused engine tests**

Run: `uv run pytest tests/unit/dst/test_engine.py -q`

Expected: fault-target and replay-path tests pass.

### Task 5: Surface Honest Coverage In Verify And Replay Outputs

**Files:**
- Modify: `/Users/rajattiwari/litmus/src/litmus/reporting/console.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/reporting/pr_comment.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/reporting/explanations.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/mcp/tools.py`
- Modify: `/Users/rajattiwari/litmus/src/litmus/runs/summary.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/reporting/test_console.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/reporting/test_pr_comment.py`
- Modify: `/Users/rajattiwari/litmus/tests/unit/mcp/test_tools.py`

**Step 1: Implement shared reporting changes**

Add boundary coverage and non-HTTP fault context to summary/explanation flows without one-off GitHub Action logic.

**Step 2: Run reporting tests**

Run: `uv run pytest tests/unit/reporting/test_console.py tests/unit/reporting/test_pr_comment.py tests/unit/mcp/test_tools.py tests/unit/replay/test_explain.py -q`

Expected: output surfaces describe coverage honestly and replay explanations mention DB/Redis context.

### Task 6: Land End-To-End Verify And Replay Regression

**Files:**
- Modify: `/Users/rajattiwari/litmus/tests/integration/test_verify_command.py`
- Modify: `/Users/rajattiwari/litmus/tests/integration/test_replay_command.py`

**Step 1: Implement the fixture-backed AcmePay-style regression**

Add a small ASGI service fixture that uses:

- `httpx`
- supported `redis.asyncio`
- supported `sqlalchemy.ext.asyncio`

Verify that a DB or Redis fault produces a breaking seed through normal `litmus verify`, persists replay artifacts, and is explained by `litmus replay seed:X`.

**Step 2: Run focused integration tests**

Run: `uv run pytest tests/integration/test_verify_command.py tests/integration/test_replay_command.py -q`

Expected: verify/replay demonstrate the shipped cross-layer moat.

### Task 7: Verify The Whole Slice

**Files:**
- Modify only files already touched above

**Step 1: Run targeted verification**

Run: `uv run pytest tests/unit/dst/test_engine.py tests/integration/dst/test_asgi_harness.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py tests/unit/replay/test_explain.py tests/unit/reporting/test_console.py tests/unit/reporting/test_pr_comment.py tests/unit/mcp/test_tools.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py -q`

Expected: PASS

**Step 2: Run broader regression verification**

Run: `uv run pytest -q`

Expected: PASS

**Step 3: Check whitespace**

Run: `git diff --check`

Expected: no output
