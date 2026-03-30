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
**Status:** partial, replay and property checkpoints in review
**Files Changed:** `src/litmus/replay/__init__.py`, `src/litmus/replay/differential.py`, `src/litmus/properties/__init__.py`, `src/litmus/properties/runner.py`, `tests/integration/replay/test_differential.py`, `tests/unit/properties/test_runner.py`, `pyproject.toml`, `uv.lock`, `.gitignore`, `product/STATUS.md`
**Tests Run:** `uv run pytest tests/unit/properties/test_runner.py -q`, `uv run pytest tests/integration/replay/test_differential.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py tests/unit/invariants/test_models.py tests/unit/invariants/test_store.py tests/unit/invariants/test_mined.py tests/unit/invariants/test_suggested.py tests/unit/scenarios/test_builder.py tests/unit/properties/test_runner.py tests/integration/replay/test_differential.py -q`, `git diff --check`
**Results:** Differential replay exists as an async comparison layer over built scenarios and skips suggested-only baselines. The property layer now runs confirmed `type=property` invariants through Hypothesis-backed counterexample search, returns shrunk failing requests, and explicitly skips suggested or non-property invariants so the deterministic verification path stays anchored to confirmed behavior.
**Open Risks:** Replay classification is still heuristic. The property runner currently infers strategies from a single request example, so generated inputs remain conservative and may miss richer domain boundaries until the invariant schema grows stronger generators or constraints.
**Next Recommended Step:** Review and stabilize the WS-04 result models, then either deepen property generation semantics or move upward into reporting/verify orchestration with the current replay and property interfaces.
