# WS-02 App Discovery, Diff Tracing, And Endpoint Mapping

## Goal

Resolve which ASGI app to load and which endpoints are affected by a code change.

## Scope

- config loading
- ASGI app reference discovery
- route extraction for FastAPI and Starlette
- changed-file and changed-symbol tracing into affected endpoints

## Out Of Scope

- scenario generation
- runtime patching
- simulator logic

## Primary Files

- `src/litmus/config.py`
- `src/litmus/discovery/app.py`
- `src/litmus/discovery/project.py`
- `src/litmus/discovery/diff.py`
- `src/litmus/discovery/routes.py`
- `src/litmus/discovery/tracing.py`

## Dependencies

- WS-01

## Interfaces To Stabilize

- `discover_app_reference()`
- `load_asgi_app()`
- `map_changed_code_to_endpoints()`

## Success Criteria

- Can locate a standard FastAPI app automatically
- Can trace changed payment-service code to the right routes in fixtures
- Test fixtures cover both explicit config and inferred discovery

## Handoff

**Workstream:** WS-02
**Status:** done
**Files Changed:** `src/litmus/config.py`, `src/litmus/discovery/app.py`, `src/litmus/discovery/project.py`, `src/litmus/discovery/diff.py`, `src/litmus/discovery/routes.py`, `src/litmus/discovery/tracing.py`, `tests/unit/discovery/`, `tests/fixtures/apps/simple_fastapi_app/`, `tests/fixtures/apps/payment_service/`
**Tests Run:** `uv run pytest tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py -q`, `uv run pytest tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py -q`, `uv run pytest tests/smoke/test_cli.py tests/unit/discovery/test_config.py tests/unit/discovery/test_app_discovery.py tests/unit/discovery/test_diff.py tests/unit/discovery/test_routes.py tests/unit/discovery/test_tracing.py -q`, `uv run litmus --help`
**Results:** Explicit config loading, AST app discovery, import-context-aware app loading, diff parsing, route extraction, and conservative changed-symbol endpoint tracing are implemented and reviewed. Review follow-ups for discovered app loading, relative imports, aliased imports, module imports, and multi-method `@app.route()` handlers are included.
**Open Risks:** `sys.modules` reuse across different repo roots remains outside the current CLI contract. Tracing is still intentionally conservative and follows only direct imports and direct call sites.
**Next Recommended Step:** Start WS-03 with invariant models, YAML persistence, and mined test extraction.
