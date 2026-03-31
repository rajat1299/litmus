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
**Status:** partial, verify/replay/watch approved with PR-comment rendering checkpoint in review
**Files Changed:** `src/litmus/dst/engine.py`, `src/litmus/replay/__init__.py`, `src/litmus/replay/trace.py`, `src/litmus/reporting/__init__.py`, `src/litmus/reporting/confidence.py`, `src/litmus/reporting/console.py`, `src/litmus/reporting/pr_comment.py`, `src/litmus/watch.py`, `src/litmus/cli.py`, `pyproject.toml`, `uv.lock`, `tests/integration/test_verify_command.py`, `tests/integration/test_replay_command.py`, `tests/integration/test_watch_mode.py`, `tests/unit/reporting/test_pr_comment.py`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/unit/reporting/test_pr_comment.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py -q`, `uv run pytest tests/smoke/test_cli.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py tests/unit/reporting/test_pr_comment.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`, `git diff --check`
**Results:** WS-07 now has a pure PR-comment renderer that turns the existing verify/replay/property result model into the launch dashboard artifact. The renderer reports confidence score, affected endpoints, layer results, failing seeds with `litmus replay` reproduction commands, and short human-readable explanations for replay regressions and failed property checks. This keeps the reporting contract explicit before wiring it into the GitHub Action surface.
**Open Risks:** The GitHub Action wrapper still does not exist, and the replay seed model is still a local deterministic artifact over replayable scenarios rather than a full DST seed/fault schedule reproduction contract. The verify/watch path also still reports over all discovered scenarios instead of a real changed-files diff input, and watch failures still surface only as simple console errors rather than richer diagnostics.
**Next Recommended Step:** Review the PR-comment rendering contract, then add the GitHub Action wrapper that runs Litmus and publishes this comment on pull requests.
