# WS-05 Deterministic Runtime And DST Scheduler

## Goal

Create the deterministic execution core that drives Litmus's hero loop.

## Scope

- simulated scheduler
- seed and fault-profile handling
- async yield-point bookkeeping
- in-process ASGI execution harness

## Out Of Scope

- concrete HTTP, DB, or Redis simulators
- confidence score calculation

## Primary Files

- `src/litmus/dst/runtime.py`
- `src/litmus/dst/scheduler.py`
- `src/litmus/dst/asgi.py`
- `src/litmus/dst/faults.py`

## Dependencies

- WS-01
- WS-02

## Interfaces To Stabilize

- seed input format
- fault schedule API
- trace event structure

## Success Criteria

- Same seed reproduces the same execution order and fault plan
- ASGI execution works without a live server
- Runtime contract is stable enough for simulator work to proceed
