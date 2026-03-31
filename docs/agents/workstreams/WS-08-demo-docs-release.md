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
**Status:** partial, demo plus packaging and release-path checkpoint in review
**Files Changed:** `examples/payment_service/app.py`, `examples/payment_service/tests/test_payment_demo.py`, `examples/payment_service/README.md`, `tests/e2e/test_demo_payment_flow.py`, `tests/e2e/test_packaging_release.py`, `docs/alpha-quickstart.md`, `docs/releases/2026-03-31-alpha.md`, `CONTRIBUTING.md`, `product/STATUS.md`, `docs/agents/workstreams/WS-08-demo-docs-release.md`
**Tests Run:** `uv run pytest tests/e2e/test_demo_payment_flow.py -q`, `uv run pytest tests/e2e/test_packaging_release.py -q`, `uv run pytest tests/e2e/test_demo_payment_flow.py tests/e2e/test_packaging_release.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py -q`, `uv run pytest tests/smoke/test_cli.py tests/e2e/test_demo_payment_flow.py tests/e2e/test_packaging_release.py tests/integration/test_verify_command.py tests/integration/test_replay_command.py tests/integration/test_watch_mode.py tests/unit/dst/test_engine.py tests/unit/github_action/test_publish.py tests/unit/github_action/test_report.py tests/unit/github_action/test_action_files.py tests/unit/reporting/test_pr_comment.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py tests/unit/simulators/test_http_semantics.py tests/unit/simulators/test_sqlalchemy_async.py tests/unit/simulators/test_redis_async.py tests/integration/simulators/test_httpx_adapter.py tests/integration/simulators/test_aiohttp_adapter.py tests/integration/simulators/test_transaction_faults.py tests/integration/simulators/test_redis_faults.py examples/payment_service/tests/test_payment_demo.py -q`, `git diff --check`
**Results:** WS-08 now covers the grounded alpha release path without touching the aspirational top-level `README.md`. The repo ships a runnable payment-service demo, example-scoped demo instructions, an end-to-end proof that `verify` fails then reruns green after a fix, a packaging smoke test that builds both wheel and sdist, installs the built wheel into a fresh virtual environment, runs the packaged `litmus` CLI, and executes the demo verify/replay flow, plus grounded alpha docs in `docs/alpha-quickstart.md` and `docs/releases/2026-03-31-alpha.md`. `CONTRIBUTING.md` now also matches the actual `uv`-based development workflow.
**Open Risks:** There is still no publish-to-index automation in the repo, and the top-level `README.md` remains intentionally aspirational rather than a source of grounded alpha install guidance. The demo is still honest to the current alpha implementation, which means it proves mined-baseline regression and replay rather than the full aspirational DST/fault-injection story.
**Next Recommended Step:** Review this WS-08 packaging and release-path checkpoint, then decide whether to stop at the current alpha state or take a later pass for publish automation and richer release engineering.
