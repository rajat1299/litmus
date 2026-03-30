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
**Status:** partial
**Files Changed:** `src/litmus/invariants/models.py`, `src/litmus/invariants/store.py`, `src/litmus/invariants/mined.py`, `tests/unit/invariants/`, `tests/fixtures/tests/test_payment.py`, dependency updates in `pyproject.toml` and `uv.lock`
**Tests Run:** `uv run pytest tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py -q`
**Results:** Invariant models, YAML persistence, and mined test extraction are implemented and reviewed. Follow-up fixes cover `state_transition`, async test mining, and skipping unsupported helper tests. Suggested invariants and scenario building are not started yet.
**Open Risks:** The miner intentionally supports only a narrow literal request/response pattern plus direct `response["status_code"]` assertions. More complex pytest fixtures or indirect assertions are still out of scope.
**Next Recommended Step:** Implement `suggest_invariants()` and `build_scenarios()` with tests before moving into replay and reporting workstreams.
