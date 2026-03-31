# WS-08 Demo App, Docs, Packaging, And Release Path

## Goal

Make the launch story runnable, reproducible, and publishable.

## Scope

- sample FastAPI payment app
- seeded failure-mode demo
- README and setup docs
- packaging and release notes for the first usable alpha

## Out Of Scope

- pricing pages
- marketing site
- enterprise workflows

## Primary Files

- `examples/payment_service/app.py`
- `examples/payment_service/tests/test_payment_demo.py`
- `examples/payment_service/README.md`
- `tests/e2e/test_demo_payment_flow.py`
- `product/STATUS.md`
- release and packaging metadata created during implementation

## Dependencies

- WS-01 through WS-07

## Success Criteria

- The demo script from the product spec works end-to-end
- Fresh users can install and run the happy-path demo locally
- The repo is understandable without external context

## Handoff

**Workstream:** WS-08
**Status:** partial, demo app and end-to-end launch slice in review
**Files Changed:** `examples/payment_service/app.py`, `examples/payment_service/tests/test_payment_demo.py`, `examples/payment_service/README.md`, `tests/e2e/test_demo_payment_flow.py`, `product/STATUS.md`, `docs/agents/workstreams/WS-08-demo-docs-release.md`
**Tests Run:** `uv run pytest tests/e2e/test_demo_payment_flow.py -q`, `uv run pytest tests/e2e/test_demo_payment_flow.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py -q`, `uv run pytest tests/smoke/test_cli.py tests/e2e/test_demo_payment_flow.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py tests/unit/dst/test_engine.py tests/unit/github_action/test_publish.py tests/unit/github_action/test_report.py tests/unit/github_action/test_action_files.py tests/unit/reporting/test_pr_comment.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py -q`, `git diff --check`
**Results:** The repo now contains a runnable payment-service demo under `examples/payment_service/` that is intentionally broken on the happy path, mined tests that define the expected contract, example-scoped demo instructions, and an end-to-end regression test that proves the current alpha loop: `litmus verify` fails, replay traces are written, `litmus replay seed:1` explains the regression, the app file is fixed, and `litmus verify` goes green on rerun. The top-level `README.md` was intentionally left untouched by explicit user direction because it remains the aspirational CLI surface rather than the grounded alpha demo surface.
**Open Risks:** Packaging and release-note polish are still pending. The demo is honest to the current alpha implementation, which means it demonstrates mined-baseline regression and replay rather than the full aspirational DST/fault-injection story from the top-level README. Fresh-user install docs also still live only inside the example folder for now because the main README was intentionally left unchanged.
**Next Recommended Step:** Review this WS-08 demo slice, then decide whether to take a follow-on packaging/release-doc pass or stop with the demo-proven alpha state.
