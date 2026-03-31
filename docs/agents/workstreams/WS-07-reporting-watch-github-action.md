# WS-07 Reporting, Watch Mode, And GitHub Action

## Goal

Turn verification results into usable developer and team workflows.

## Scope

- console reporting
- confidence score aggregation
- replay-trace presentation
- `litmus watch`
- GitHub Action and PR-comment rendering

## Out Of Scope

- web dashboard
- MCP server

## Primary Files

- `src/litmus/dst/engine.py`
- `src/litmus/replay/trace.py`
- `src/litmus/reporting/confidence.py`
- `src/litmus/reporting/console.py`
- `src/litmus/reporting/pr_comment.py`
- `src/litmus/watch.py`
- `.github/workflows/litmus.yml`
- `action.yml`

## Dependencies

- WS-03
- WS-04
- WS-05
- WS-06

## Success Criteria

- `litmus verify` produces a clear endpoint-level report
- `litmus replay <seed>` is understandable without internal knowledge
- PR comments are strong enough to function as the launch dashboard

## Handoff

**Workstream:** WS-07
**Status:** partial, verify and shared reporting checkpoint in review
**Files Changed:** `src/litmus/dst/engine.py`, `src/litmus/reporting/__init__.py`, `src/litmus/reporting/confidence.py`, `src/litmus/reporting/console.py`, `src/litmus/cli.py`, `tests/integration/test_verify_command.py`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/integration/test_verify_command.py -q`, `uv run pytest tests/smoke/test_cli.py tests/integration/test_verify_command.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`, `git diff --check`
**Results:** `litmus verify` now runs a real end-to-end composition over the existing discovery, mined invariants, scenario builder, ASGI harness, differential replay, and property layers. The new engine produces a shared verification result model, console reporting summarizes route/invariant/scenario counts plus replay/property tallies and confidence, and the CLI exits non-zero only when breaking replay or failed property signals are present.
**Open Risks:** This is only the first WS-07 slice. `litmus replay` still lacks trace serialization, `litmus watch` is still a stub, GitHub Action / PR comment rendering does not exist yet, and the verify path currently reports over all discovered scenarios instead of a real changed-files diff input.
**Next Recommended Step:** Review and stabilize the `verify` result/reporting contract, then add replay trace serialization and the `litmus replay` command as the next WS-07 checkpoint.
