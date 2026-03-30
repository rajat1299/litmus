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
