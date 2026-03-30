# Litmus v0.1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Python-first Litmus v0.1 product: a local CLI and GitHub Action that verify changed FastAPI and Starlette request flows using invariants, property tests, differential replay, and deterministic simulation testing with zero-config patching.

**Architecture:** The product is a Python package with a CLI entrypoint, a project-discovery layer, an invariant and scenario pipeline, a deterministic runtime with semantic simulators, and reporting surfaces for terminal and GitHub. The launch stack is intentionally narrow so the zero-config DST loop is reliable, fast, and demonstrable.

**Tech Stack:** Python 3.11, `uv`, Typer, Rich, PyYAML, Pydantic, pytest, Hypothesis, FastAPI/Starlette fixtures, GitHub Actions, watchfiles, and optional OpenAI-compatible LLM integration.

---

## Execution Notes

- Implement in a dedicated worktree once the repository is initialized with git.
- Task 1 must land before the other tasks start.
- After Task 1, Tasks 2, 4, and 6 can start in parallel.
- Tasks 7 and 8 depend on the runtime and simulator contracts from Task 6.
- Task 10 is the integration checkpoint and should not start until Tasks 2 through 9 are stable.

### Task 1: Bootstrap The Python Package And CLI Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/litmus/__init__.py`
- Create: `src/litmus/main.py`
- Create: `src/litmus/cli.py`
- Test: `tests/smoke/test_cli.py`

**Step 1: Write the failing smoke test**

Create `tests/smoke/test_cli.py` with a failing import and command assertion for `litmus --help`.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/smoke/test_cli.py -q`
Expected: FAIL with import error or missing CLI app

**Step 3: Write minimal implementation**

Create a Typer app with placeholder commands:

- `litmus init`
- `litmus verify`
- `litmus watch`
- `litmus replay`

Wire `src/litmus/main.py` as the console entrypoint.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/smoke/test_cli.py -q`
Expected: PASS

**Step 5: Commit**

Run:

```bash
git add pyproject.toml .gitignore README.md src/litmus tests/smoke/test_cli.py
git commit -m "chore: bootstrap litmus package and cli"
```

### Task 2: Add Project Config And ASGI App Discovery

**Files:**
- Create: `src/litmus/config.py`
- Create: `src/litmus/discovery/__init__.py`
- Create: `src/litmus/discovery/app.py`
- Create: `src/litmus/discovery/project.py`
- Test: `tests/unit/discovery/test_config.py`
- Test: `tests/unit/discovery/test_app_discovery.py`
- Test Fixture: `tests/fixtures/apps/simple_fastapi_app/main.py`

**Step 1: Write the failing tests**

Cover:

- loading `litmus.yaml`
- falling back to `pyproject.toml`
- AST detection of `FastAPI()` or `Starlette()` app objects

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py -q`
Expected: FAIL with missing modules or functions

**Step 3: Write minimal implementation**

Implement:

- `load_repo_config()`
- `discover_app_reference()`
- `load_asgi_app(reference: str)`

Support the resolution order defined in the product spec.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/config.py src/litmus/discovery tests/unit/discovery tests/fixtures/apps/simple_fastapi_app
git commit -m "feat: add config loading and asgi app discovery"
```

### Task 3: Build Diff Parsing And Endpoint Mapping

**Files:**
- Create: `src/litmus/discovery/diff.py`
- Create: `src/litmus/discovery/routes.py`
- Create: `src/litmus/discovery/tracing.py`
- Test: `tests/unit/discovery/test_diff.py`
- Test: `tests/unit/discovery/test_routes.py`
- Test: `tests/unit/discovery/test_tracing.py`
- Test Fixture: `tests/fixtures/apps/payment_service/`

**Step 1: Write the failing tests**

Cover:

- parsing changed files from git diff output
- extracting routes from FastAPI/Starlette decorators
- tracing changed symbols to route handlers

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:

- `parse_changed_files()`
- `extract_routes()`
- `map_changed_code_to_endpoints()`

Use AST-first logic and keep import tracing conservative.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/discovery tests/unit/discovery tests/fixtures/apps/payment_service
git commit -m "feat: trace changed code to affected endpoints"
```

### Task 4: Add Invariant Models, Store, And Mined Test Extraction

**Files:**
- Create: `src/litmus/invariants/__init__.py`
- Create: `src/litmus/invariants/models.py`
- Create: `src/litmus/invariants/store.py`
- Create: `src/litmus/invariants/mined.py`
- Test: `tests/unit/invariants/test_models.py`
- Test: `tests/unit/invariants/test_store.py`
- Test: `tests/unit/invariants/test_mined.py`
- Test Fixture: `tests/fixtures/tests/test_payment.py`

**Step 1: Write the failing tests**

Cover:

- invariant serialization to YAML
- `confirmed` vs `suggested` status handling
- extracting baseline scenarios from pytest-style tests and fixtures

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:

- invariant Pydantic models
- YAML load and save helpers
- pytest mining logic for simple request/response fixtures

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/invariants tests/unit/invariants tests/fixtures/tests/test_payment.py
git commit -m "feat: add invariant store and mined test extraction"
```

### Task 5: Add Suggested Invariants, Scenario Builder, And Differential Replay

**Files:**
- Create: `src/litmus/invariants/suggested.py`
- Create: `src/litmus/scenarios/__init__.py`
- Create: `src/litmus/scenarios/builder.py`
- Create: `src/litmus/replay/__init__.py`
- Create: `src/litmus/replay/differential.py`
- Test: `tests/unit/invariants/test_suggested.py`
- Test: `tests/unit/scenarios/test_builder.py`
- Test: `tests/integration/replay/test_differential.py`

**Step 1: Write the failing tests**

Cover:

- provider-agnostic LLM suggestion interface
- combining mined and suggested scenarios
- replaying a baseline input against changed code and comparing outputs

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/integration/replay/test_differential.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:

- `suggest_invariants()`
- `build_scenarios()`
- `run_differential_replay()`

Keep LLM calls behind an interface so the verification path stays deterministic.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/integration/replay/test_differential.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/invariants/suggested.py src/litmus/scenarios src/litmus/replay tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/integration/replay/test_differential.py
git commit -m "feat: add scenario builder and differential replay"
```

### Task 6: Build The Deterministic Runtime And ASGI Execution Harness

**Files:**
- Create: `src/litmus/dst/__init__.py`
- Create: `src/litmus/dst/runtime.py`
- Create: `src/litmus/dst/scheduler.py`
- Create: `src/litmus/dst/asgi.py`
- Create: `src/litmus/dst/faults.py`
- Test: `tests/unit/dst/test_scheduler.py`
- Test: `tests/unit/dst/test_faults.py`
- Test: `tests/integration/dst/test_asgi_harness.py`

**Step 1: Write the failing tests**

Cover:

- deterministic seed scheduling
- fault plan lookup
- in-process ASGI invocation through `app(scope, receive, send)`

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/dst/test_asgi_harness.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:

- deterministic scheduler
- fault profile model
- ASGI harness that captures status code, body, and trace metadata

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/dst/test_asgi_harness.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/dst tests/unit/dst tests/integration/dst
git commit -m "feat: add deterministic runtime and asgi harness"
```

### Task 7: Add HTTP Simulators And Patching Adapters

**Files:**
- Create: `src/litmus/simulators/__init__.py`
- Create: `src/litmus/simulators/base.py`
- Create: `src/litmus/simulators/http.py`
- Create: `src/litmus/simulators/httpx_adapter.py`
- Create: `src/litmus/simulators/aiohttp_adapter.py`
- Test: `tests/unit/simulators/test_http_semantics.py`
- Test: `tests/integration/simulators/test_httpx_adapter.py`
- Test: `tests/integration/simulators/test_aiohttp_adapter.py`

**Step 1: Write the failing tests**

Cover:

- URL-pattern response fixtures
- timeout, connection refusal, 500, and slow-response injection
- adapter patching and unpatching lifecycle

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/simulators/test_http_semantics.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:

- shared HTTP simulator state model
- `patch_httpx()`
- `patch_aiohttp()`

Use deterministic latency and fault schedules driven by the DST runtime.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/simulators/test_http_semantics.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/simulators tests/unit/simulators tests/integration/simulators
git commit -m "feat: add deterministic http simulators"
```

### Task 8: Add SQLAlchemy Async And Redis Async Semantic Simulators

**Files:**
- Create: `src/litmus/simulators/sqlalchemy_async.py`
- Create: `src/litmus/simulators/redis_async.py`
- Test: `tests/unit/simulators/test_sqlalchemy_async.py`
- Test: `tests/unit/simulators/test_redis_async.py`
- Test: `tests/integration/simulators/test_transaction_faults.py`
- Test: `tests/integration/simulators/test_redis_faults.py`

**Step 1: Write the failing tests**

Cover:

- CRUD semantics
- transaction begin, commit, rollback
- connection drops, pool exhaustion, and partial writes
- key expiry and blocking list behavior in Redis

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement enough semantic behavior for the launch demo and core app patterns. Keep unsupported backend features explicit and documented.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/simulators/sqlalchemy_async.py src/litmus/simulators/redis_async.py tests/unit/simulators tests/integration/simulators
git commit -m "feat: add semantic database and redis simulators"
```

### Task 9: Compose Verify, Replay, Reporting, And Watch Mode

**Files:**
- Create: `src/litmus/dst/engine.py`
- Create: `src/litmus/replay/trace.py`
- Create: `src/litmus/reporting/__init__.py`
- Create: `src/litmus/reporting/confidence.py`
- Create: `src/litmus/reporting/console.py`
- Create: `src/litmus/reporting/pr_comment.py`
- Create: `src/litmus/watch.py`
- Modify: `src/litmus/cli.py`
- Test: `tests/integration/test_verify_command.py`
- Test: `tests/integration/test_replay_command.py`
- Test: `tests/integration/test_watch_mode.py`

**Step 1: Write the failing integration tests**

Cover:

- end-to-end `litmus verify`
- replaying a failing seed
- file-change triggered watch runs

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:

- `run_verification()`
- trace serialization for replay
- confidence score aggregation
- Rich console output
- watchfiles-driven reruns

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/litmus/dst/engine.py src/litmus/replay/trace.py src/litmus/reporting src/litmus/watch.py src/litmus/cli.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py
git commit -m "feat: add verify replay watch and reporting flows"
```

### Task 10: Add GitHub Action, Demo App, Packaging, And Release Checks

**Files:**
- Create: `.github/workflows/litmus.yml`
- Create: `action.yml`
- Create: `src/litmus/github_action/__init__.py`
- Create: `src/litmus/github_action/report.py`
- Create: `examples/payment_service/app.py`
- Create: `examples/payment_service/tests/test_payment.py`
- Test: `tests/e2e/test_demo_payment_flow.py`
- Modify: `README.md`

**Step 1: Write the failing end-to-end test**

Cover the launch demo path:

- agent-style retry logic bug in the sample payment service
- verify command catches a deterministic double-charge seed
- replay command reproduces the failure

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/e2e/test_demo_payment_flow.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:

- GitHub Action wrapper
- PR-comment renderer
- sample FastAPI payment app with an intentional failure mode
- README setup and demo instructions

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/e2e/test_demo_payment_flow.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add .github/workflows/litmus.yml action.yml src/litmus/github_action examples/payment_service tests/e2e/test_demo_payment_flow.py README.md
git commit -m "feat: add github action and launch demo flow"
```

---

## Completion Checklist

- `product/STATUS.md` is updated as each task starts and finishes.
- Every workstream packet in `docs/agents/workstreams/` is kept aligned with implementation reality.
- The 10-second local budget is measured during Tasks 6 through 10, not deferred to the end.
- Before calling the product launch-ready, run the full test suite plus the demo workflow and capture the results in `product/STATUS.md`.
