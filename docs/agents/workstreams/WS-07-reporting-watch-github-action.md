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
**Status:** partial, verify/replay approved with watch checkpoint in review
**Files Changed:** `src/litmus/dst/engine.py`, `src/litmus/replay/__init__.py`, `src/litmus/replay/trace.py`, `src/litmus/reporting/__init__.py`, `src/litmus/reporting/confidence.py`, `src/litmus/reporting/console.py`, `src/litmus/watch.py`, `src/litmus/cli.py`, `pyproject.toml`, `uv.lock`, `tests/integration/test_verify_command.py`, `tests/integration/test_replay_command.py`, `tests/integration/test_watch_mode.py`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py -q`, `uv run pytest tests/smoke/test_cli.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`, `git diff --check`
**Results:** `litmus watch` now uses `watchfiles` to observe repo changes, filters out Litmus’s own `.litmus` artifact writes to avoid self-trigger loops, reruns verification on relevant source/config changes, persists fresh replay traces after each rerun, and prints the same verification summary used by `litmus verify`. The CLI exits cleanly on `Ctrl-C`, and the watch loop is testable through an injected watcher seam for deterministic integration coverage.
**Open Risks:** GitHub Action / PR comment rendering does not exist yet, and the replay seed model is still a local deterministic artifact over replayable scenarios rather than a full DST seed/fault schedule reproduction contract. The verify/watch path also still reports over all discovered scenarios instead of a real changed-files diff input, and watch currently surfaces verification exceptions as plain console errors rather than structured diagnostics.
**Next Recommended Step:** Review the watch loop contract, then add PR-comment and GitHub Action rendering on top of the current verify/replay/watch result model.
