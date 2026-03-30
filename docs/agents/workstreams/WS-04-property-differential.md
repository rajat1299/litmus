# WS-04 Property Checks And Differential Replay

## Goal

Implement the non-DST verification layers that ground the verdict and catch regressions.

## Scope

- Hypothesis-backed property execution
- differential replay against mined scenarios
- comparison and classification of output divergence

## Out Of Scope

- LLM generation
- DST scheduler
- console reporting polish beyond what tests require

## Primary Files

- `src/litmus/properties/runner.py`
- `src/litmus/replay/differential.py`
- `tests/unit/properties/`
- `tests/integration/replay/`

## Dependencies

- WS-01
- WS-03

## Success Criteria

- Property checks can execute against confirmed and approved invariants
- Differential replay can compare baseline and changed behavior deterministically
- Result objects are reusable by the reporting layer
