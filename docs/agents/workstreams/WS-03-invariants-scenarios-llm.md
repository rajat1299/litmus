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
