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

## Handoff

**Workstream:** WS-04
**Status:** partial, differential replay checkpoint in review
**Files Changed:** `src/litmus/replay/__init__.py`, `src/litmus/replay/differential.py`, `tests/integration/replay/test_differential.py`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/integration/replay/test_differential.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/integration/replay/test_differential.py -q`, `git diff --check`
**Results:** Differential replay now exists as an async comparison layer over built scenarios. It skips scenarios with no baseline response, replays changed behavior via a runner interface, computes field-level response diffs, and classifies outcomes as `unchanged`, `breaking_change`, `benign_change`, or `improvement`.
**Open Risks:** Classification is intentionally heuristic in this checkpoint. Status-code rank changes drive `breaking_change` vs `improvement`, while same-rank body-only changes are classified as `benign_change`. More domain-aware classification may be needed once real ASGI execution and reporting consume these results.
**Next Recommended Step:** Review and stabilize the replay result model, then implement WS-04 property-check execution on top of the confirmed invariant set.
