# WS-01 Repo And CLI Foundation

## Goal

Create the initial Python package, tooling, and CLI skeleton that every other workstream depends on.

## Scope

- Python package layout
- `pyproject.toml`
- CLI entrypoint and placeholder commands
- basic test harness
- repo-level developer tooling

## Out Of Scope

- ASGI discovery
- DST logic
- simulator behavior

## Primary Files

- `pyproject.toml`
- `README.md`
- `src/litmus/__init__.py`
- `src/litmus/main.py`
- `src/litmus/cli.py`
- `tests/smoke/test_cli.py`

## Dependencies

None.

## Success Criteria

- `uv run pytest tests/smoke/test_cli.py -q` passes
- CLI commands exist and return placeholder output
- later workstreams can import shared package modules cleanly

## Handoff Notes

Publish any package-management or entrypoint decisions here before closing.
