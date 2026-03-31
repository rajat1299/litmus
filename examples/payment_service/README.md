# Payment Service Demo

This example is the grounded WS-08 demo for the current Litmus alpha.

It intentionally starts in a broken state:

- mined tests say `POST /payments/charge` should return `200 {"status": "charged"}` for a normal amount
- the current `app.py` returns `500 {"status": "duplicate_charge_risk"}`
- `litmus verify` should fail
- `litmus replay seed:1` should explain the regression

## Run The Demo

From this example directory:

```bash
uv run --project ../.. litmus verify
```

Expected shape:

```text
Litmus verify
App: app:app
Routes: 1
Invariants: 2
Scenarios: 2
Replay: unchanged=1 breaking=1 benign=0 improvement=0
Properties: passed=0 failed=0 skipped=0
Confidence: 0.50
```

Replay the failing scenario:

```bash
uv run --project ../.. litmus replay seed:1
```

Expected shape:

```text
Litmus replay
Seed: seed:1
Route: POST /payments/charge
Baseline: 200 {'status': 'charged'}
Current: 500 {'status': 'duplicate_charge_risk'}
Classification: breaking_change
```

## Fix The Demo

Replace the happy-path branch in `charge_with_retry(...)` with the shipped contract:

```python
if amount > 500:
    return {"status_code": 402, "json": {"status": "declined"}}
return {"status_code": 200, "json": {"status": "charged"}}
```

Then rerun:

```bash
uv run --project ../.. litmus verify
```

Expected shape:

```text
Replay: unchanged=2 breaking=0 benign=0 improvement=0
Confidence: 1.00
```

This demo is intentionally narrower than the aspirational top-level repo README. It proves the current alpha loop that exists in code today: mined baselines, deterministic replay artifacts, and rerun-to-green after a fix.
