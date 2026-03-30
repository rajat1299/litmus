# WS-08 Demo App, Docs, Packaging, And Release Path

## Goal

Make the launch story runnable, reproducible, and publishable.

## Scope

- sample FastAPI payment app
- seeded failure-mode demo
- README and setup docs
- packaging and release notes for the first usable alpha

## Out Of Scope

- pricing pages
- marketing site
- enterprise workflows

## Primary Files

- `examples/payment_service/app.py`
- `examples/payment_service/tests/test_payment.py`
- `tests/e2e/test_demo_payment_flow.py`
- `README.md`
- release and packaging metadata created during implementation

## Dependencies

- WS-01 through WS-07

## Success Criteria

- The demo script from the product spec works end-to-end
- Fresh users can install and run the happy-path demo locally
- The repo is understandable without external context
