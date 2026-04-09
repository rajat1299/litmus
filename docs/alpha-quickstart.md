# Litmus Alpha Quickstart

This guide is the grounded quickstart for the current alpha. It is the source of truth for the shipped Litmus surface in this repository today.

The top-level `README.md` remains the aspirational product surface. Use this document when you want the commands and flows that are verified in the repo right now.

Current grounded alpha surface:

- Python 3.11+
- local CLI: `litmus init`, `litmus verify`, `litmus watch`, `litmus replay`, `litmus invariants ...`, `litmus config set ...`
- local stdio MCP server via `litmus mcp`
- replay over the latest replayable local run artifacts under `.litmus/runs/`
- compatibility and degradation contract documented in `docs/alpha-compatibility.md`
- local fault-profile controls are grounded presets: `default`, `gentle`, and `hostile`
- local decision-policy controls are grounded repo-local profiles: `alpha_local_v1` and `strict_local_v1`
- per-run policy overrides are grounded on `litmus verify --decision-policy ...`, MCP `verify(decision_policy=...)`, and the GitHub Action `decision-policy` input

Performance contract:

- local `litmus verify` runs are budgeted to stay within 10 seconds on the grounded launch fixture path
- CI verification runs are budgeted within 60 seconds
- the default local launch budget uses 3 replay seeds per scenario and 100 property examples
- the grounded CI budget uses 500 replay seeds per scenario and 500 property examples
- Only the default local profile is the grounded under-10-second launch path.
- The hostile profile is a deeper local opt-in path rather than the default launch contract.

Install-channel note:

- package build and publish are now automated through the repository release workflow
- tag pushes publish to PyPI; manual dispatch can rerun the workflow as a build-only preflight, or publish from a `v*` tag when the `publish` input is explicitly enabled
- Homebrew is explicitly deferred from the grounded alpha surface

## Prerequisites

- Python 3.11+
- `uv`
- Git

## Local Dev Setup

```bash
git clone https://github.com/rajat1299/litmus.git
cd litmus
uv sync --group dev
uv run pytest
```

## Build The Package

```bash
uv build --out-dir dist
```

The repository release path automates this same build through GitHub Actions on release tags. Manual dispatch is available for preflight builds and controlled tag-scoped republishes. Homebrew is still deferred; do not treat `brew install litmus` as a grounded alpha path.

Expected artifacts:

- one wheel in `dist/`
- one source distribution in `dist/`

## Install The Built Wheel In A Fresh Environment

```bash
python -m venv /tmp/litmus-alpha
/tmp/litmus-alpha/bin/python -m pip install --upgrade pip
uv pip install --python /tmp/litmus-alpha/bin/python dist/*.whl
```

Smoke check:

```bash
/tmp/litmus-alpha/bin/litmus --help
```

## Run The Demo Repo

The grounded demo lives under `examples/payment_service`.

From the example directory, using the repo-managed environment:

```bash
cd examples/payment_service
uv run --project ../.. litmus verify
```

The shipped demo is intentionally broken on the happy path. Expected output shape:

```text
Litmus verify
Decision: unsafe
Merge recommendation: block
Risk: high classes=reliability,correctness
Evidence: signals=2 detected_boundaries=0 unsupported_gaps=0 pending_review=0
Policy: alpha_local_v1 failing=blocking_regressions warnings=none
App: app:app
Routes: 1
Invariants: 2
Scenarios: 2
Replay: unchanged=1 breaking=1 benign=0 improvement=0
Properties: passed=0 failed=0 skipped=0
Performance: elapsed=0.70s budget<=10.00s mode=local profile=default strategy=balanced within_budget=yes
Launch budgets: replay_seeds/scenario=3 property_examples=100
Budget policy: launch-default under-10s path
Confidence: 0.50
```

Replay the stored failure:

```bash
uv run --project ../.. litmus replay seed:1
```

Expected output shape:

```text
Litmus replay
Seed: seed:1
Route: POST /payments/charge
Baseline: 200 {'status': 'charged'}
Current: 500 {'status': 'duplicate_charge_risk'}
Classification: breaking_change
```

The grounded replay contract in this alpha is:

- `litmus replay seed:N` replays a stored seed from the latest replayable local run
- replay uses the recorded fault schedule for that stored seed
- replay is local and file-backed, not a remote or hosted execution service
- replay explanations now include the same bounded compatibility states used by verify and MCP

## Run The Local MCP Server

Litmus also ships a local stdio MCP server for the same grounded alpha surface:

```bash
uv run --project ../.. litmus mcp
```

This MCP surface is intentionally local:

- transport: stdio only
- scope: current workspace
- tools: `verify`, `list_invariants`, `replay`, `explain_failure`
- results: structured payloads backed by the same local run and replay artifacts as the CLI, including local risk assessment, evidence, policy evaluation, verification verdict, compatibility, and degradation status

## Compatibility Contract

The grounded launch matrix and honest-degradation rules now live in `docs/alpha-compatibility.md`.

Use that document when you need:

- the supported launch matrix for Python, ASGI discovery, `httpx` / `aiohttp`, SQLAlchemy async, and Redis async
- the bounded constructor and adapter shapes Litmus actually intercepts
- the meaning of `supported`, `unsupported`, `detected only`, and `not detected` in CLI, replay, PR, run-artifact, and MCP output

## Fix The Demo

In `examples/payment_service/app.py`, replace the happy-path return value with:

```python
return {"status_code": 200, "json": {"status": "charged"}}
```

Then rerun:

```bash
uv run --project ../.. litmus verify
```

Expected output shape:

```text
Decision: safe
Merge recommendation: allow
Replay: unchanged=2 breaking=0 benign=0 improvement=0
Performance: elapsed=0.65s budget<=10.00s mode=local profile=default strategy=balanced within_budget=yes
Budget policy: launch-default under-10s path
Confidence: 1.00
```

## What This Alpha Actually Proves

- mined tests become the replay baseline
- `litmus verify` writes replay artifacts under `.litmus/`
- `litmus verify` now persists a local decision bundle with risk, evidence, policy, and verdict into those run artifacts
- repo config can now switch local merge policy between the default `alpha_local_v1` and a stricter `strict_local_v1` profile without changing the shared four-value decision contract
- `litmus replay <seed>` reproduces a failing scenario from those artifacts
- a concrete app fix can be rerun to green

This alpha does not yet prove the full aspirational DST product story described in the main repo README, and it still does not include a hosted control plane. The system of record remains local and file-backed in this repository.
