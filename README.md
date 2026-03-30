# Litmus

Litmus is a Python-first verification CLI for agent-written code.

The v0.1 launch target in this repository is a local and CI workflow for FastAPI
and Starlette services that layers invariants, differential replay, and
deterministic simulation testing behind a single `litmus` command.

## Current Status

The repository is in active implementation. The CLI currently exposes the launch
command surface with placeholder behavior for:

- `litmus init`
- `litmus verify`
- `litmus watch`
- `litmus replay`
