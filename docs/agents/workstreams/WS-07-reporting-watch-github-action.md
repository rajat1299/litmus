# WS-07 Reporting, Watch Mode, And GitHub Action

## Goal

Turn verification results into usable developer and team workflows.

## Scope

- console reporting
- confidence score aggregation
- replay-trace presentation
- `litmus watch`
- GitHub Action and PR-comment rendering

## Out Of Scope

- web dashboard
- MCP server

## Primary Files

- `src/litmus/dst/engine.py`
- `src/litmus/replay/trace.py`
- `src/litmus/reporting/confidence.py`
- `src/litmus/reporting/console.py`
- `src/litmus/reporting/pr_comment.py`
- `src/litmus/watch.py`
- `.github/workflows/litmus.yml`
- `action.yml`

## Dependencies

- WS-03
- WS-04
- WS-05
- WS-06

## Success Criteria

- `litmus verify` produces a clear endpoint-level report
- `litmus replay <seed>` is understandable without internal knowledge
- PR comments are strong enough to function as the launch dashboard
