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
**Status:** partial, verify/replay/watch/reporting are approved and the GitHub Action publication checkpoint is in review
**Files Changed:** `src/litmus/dst/engine.py`, `src/litmus/replay/__init__.py`, `src/litmus/replay/trace.py`, `src/litmus/reporting/__init__.py`, `src/litmus/reporting/confidence.py`, `src/litmus/reporting/console.py`, `src/litmus/reporting/pr_comment.py`, `src/litmus/watch.py`, `src/litmus/cli.py`, `src/litmus/github_action/__init__.py`, `src/litmus/github_action/publish.py`, `src/litmus/github_action/report.py`, `action.yml`, `.github/workflows/litmus.yml`, `pyproject.toml`, `uv.lock`, `tests/integration/test_verify_command.py`, `tests/integration/test_replay_command.py`, `tests/integration/test_watch_mode.py`, `tests/unit/reporting/test_pr_comment.py`, `tests/unit/github_action/test_publish.py`, `tests/unit/github_action/test_report.py`, `tests/unit/github_action/test_action_files.py`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/unit/github_action/test_publish.py tests/unit/github_action/test_report.py tests/unit/github_action/test_action_files.py -q`, `uv run pytest tests/unit/github_action/test_publish.py tests/unit/github_action/test_report.py tests/unit/github_action/test_action_files.py tests/unit/reporting/test_pr_comment.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py -q`, `uv run pytest tests/smoke/test_cli.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py tests/unit/dst/test_engine.py tests/unit/github_action/test_publish.py tests/unit/github_action/test_report.py tests/unit/github_action/test_action_files.py tests/unit/reporting/test_pr_comment.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`, `git diff --check`
**Results:** WS-07 now ships the end-to-end GitHub Action path. The action-facing report module still runs verification against the checked-out workspace, persists replay traces, writes step-summary content plus a PR-comment markdown artifact, emits GitHub outputs for confidence/verdict/comment-path, and exits non-zero when Litmus finds critical failures or drops below the configured minimum score. On pull request events, it now also upserts a single Litmus PR comment through the GitHub REST API using a hidden marker so repeated runs refresh the existing dashboard instead of posting duplicates. The local dogfood workflow now passes the GitHub token into the action via `uses: ./`.
**Open Risks:** The replay seed model is still a local deterministic artifact over replayable scenarios rather than a full DST seed/fault schedule reproduction contract. The verify/watch/action path also still reports over all discovered scenarios instead of a real changed-files diff input, and watch failures still surface only as simple console errors rather than richer diagnostics. GitHub Action publication also currently relies on a simple issue-comment upsert path and does not yet surface richer API failure diagnostics.
**Next Recommended Step:** Review the GitHub Action publication checkpoint, then move to the demo app, README, and release-path slice that proves the launch flow end to end.
