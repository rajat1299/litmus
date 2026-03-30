# WS-05 Deterministic Runtime And DST Scheduler

## Goal

Create the deterministic execution core that drives Litmus's hero loop.

## Scope

- simulated scheduler
- seed and fault-profile handling
- async yield-point bookkeeping
- in-process ASGI execution harness

## Out Of Scope

- concrete HTTP, DB, or Redis simulators
- confidence score calculation

## Primary Files

- `src/litmus/dst/runtime.py`
- `src/litmus/dst/scheduler.py`
- `src/litmus/dst/asgi.py`
- `src/litmus/dst/faults.py`

## Dependencies

- WS-01
- WS-02

## Interfaces To Stabilize

- seed input format
- fault schedule API
- trace event structure

## Success Criteria

- Same seed reproduces the same execution order and fault plan
- ASGI execution works without a live server
- Runtime contract is stable enough for simulator work to proceed

## Handoff

**Workstream:** WS-05
**Status:** partial, deterministic runtime checkpoint in review
**Files Changed:** `src/litmus/dst/__init__.py`, `src/litmus/dst/runtime.py`, `src/litmus/dst/scheduler.py`, `src/litmus/dst/asgi.py`, `src/litmus/dst/faults.py`, `tests/unit/dst/test_scheduler.py`, `tests/unit/dst/test_faults.py`, `tests/integration/dst/test_asgi_harness.py`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/dst/test_asgi_harness.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/unit/dst/test_scheduler.py tests/unit/dst/test_faults.py tests/integration/replay/test_differential.py tests/integration/dst/test_asgi_harness.py -q`, `git diff --check`
**Results:** The DST layer now has a stable minimal runtime surface. The scheduler reproduces the same order for the same seed, the fault-plan model deterministically derives and looks up scheduled faults, and the ASGI harness runs apps in-process without a live server while capturing status, decoded body, and trace events.
**Open Risks:** This checkpoint does not yet inject faults into execution or record real async yield points; it only stabilizes the shape of the scheduler, fault plan, and ASGI trace surfaces. Simulators still depend on later runtime integration work.
**Next Recommended Step:** Review and stabilize these DST interfaces, then implement WS-06 semantic simulators against the current fault-plan and ASGI harness contracts.
