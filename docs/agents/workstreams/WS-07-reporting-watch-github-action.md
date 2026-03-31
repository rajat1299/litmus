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
**Status:** partial, verify approved with replay trace checkpoint in review
**Files Changed:** `src/litmus/dst/engine.py`, `src/litmus/replay/__init__.py`, `src/litmus/replay/trace.py`, `src/litmus/reporting/__init__.py`, `src/litmus/reporting/confidence.py`, `src/litmus/reporting/console.py`, `src/litmus/cli.py`, `.gitignore`, `tests/integration/test_verify_command.py`, `tests/integration/test_replay_command.py`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/integration/test_verify_command.py tests/integration/test_replay_command.py -q`, `uv run pytest tests/smoke/test_cli.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`, `git diff --check`
**Results:** `litmus verify` now persists deterministic replay records under `.litmus/`, assigning stable `seed:N` identifiers across replayable scenarios. `litmus replay <seed>` loads one of those records, reruns the stored scenario against the current app with the same seed value, recomputes the differential classification against the stored baseline, and prints a human-readable replay trace summary with route, baseline/current responses, classification, and ordered trace events.
**Open Risks:** `litmus watch` is still a stub, GitHub Action / PR comment rendering does not exist yet, and the replay seed model is still a local deterministic artifact over replayable scenarios rather than a full DST seed/fault schedule reproduction contract. The verify path also still reports over all discovered scenarios instead of a real changed-files diff input.
**Next Recommended Step:** Review and stabilize the replay artifact and CLI contract, then add `litmus watch` on top of the current verify/replay result model before moving into GitHub Action rendering.
