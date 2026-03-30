# WS-03 Invariants, Scenario Sourcing, And LLM Suggestions

## Goal

Build the data models and pipelines that turn existing tests into grounded invariants and extend them with suggested invariants and scenarios.

## Scope

- invariant schema and YAML persistence
- mined-test extraction
- suggested invariant interface for LLM providers
- combined scenario model

## Out Of Scope

- differential replay execution
- DST runtime
- simulator behavior

## Primary Files

- `src/litmus/invariants/models.py`
- `src/litmus/invariants/store.py`
- `src/litmus/invariants/mined.py`
- `src/litmus/invariants/suggested.py`
- `src/litmus/scenarios/builder.py`

## Dependencies

- WS-01
- WS-02

## Interfaces To Stabilize

- invariant status enum: `confirmed` vs `suggested`
- `suggest_invariants()`
- `build_scenarios()`

## Success Criteria

- Mined tests are persisted as confirmed invariants
- Suggested invariants are kept separate and explainable
- Scenario objects can be consumed by both replay and DST layers

## Handoff

**Workstream:** WS-03
**Status:** partial, Task 5 checkpoint in review
**Files Changed:** `src/litmus/invariants/models.py`, `src/litmus/invariants/store.py`, `src/litmus/invariants/mined.py`, `src/litmus/invariants/suggested.py`, `src/litmus/scenarios/__init__.py`, `src/litmus/scenarios/builder.py`, `tests/unit/invariants/`, `tests/unit/scenarios/`, `tests/fixtures/tests/test_payment.py`, dependency updates in `pyproject.toml` and `uv.lock`
**Tests Run:** `uv run pytest tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py -q`
**Results:** Suggested invariant support is now implemented behind a provider-agnostic interface, `Invariant` includes optional `reasoning` for explainable LLM suggestions, and the scenario builder groups matching confirmed and suggested invariants into endpoint/request-specific scenarios. This checkpoint intentionally stops at the WS-03 boundary and does not implement differential replay.
**Open Risks:** Suggested invariants without a request example are not promoted into scenarios yet, so provider implementations still need to supply enough request context for replay and DST to consume them. The miner also still supports only a narrow literal request/response pattern plus direct `response["status_code"]` assertions.
**Next Recommended Step:** Review and stabilize `suggest_invariants()` and `build_scenarios()`, then hand off `run_differential_replay()` to WS-04.
