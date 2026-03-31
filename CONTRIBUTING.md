# contributing to litmus

thanks for wanting to contribute. litmus is early and moving fast — the best contributions right now are simulation adapters, bug reports with reproducible seeds, and invariant packs for common patterns.

this doc covers how to get set up, what to work on, and how we review.

---

## table of contents

- [setup](#setup)
- [architecture at a glance](#architecture)
- [what to work on](#what-to-work-on)
- [writing a simulation adapter](#writing-a-simulation-adapter)
- [writing an invariant pack](#writing-an-invariant-pack)
- [testing your changes](#testing)
- [submitting a pr](#submitting-a-pr)
- [code style](#code-style)
- [reporting bugs](#reporting-bugs)
- [community](#community)

---

<a name="setup"></a>
## setup

```bash
# clone
git clone https://github.com/rajat1299/litmus.git
cd litmus

# sync the project environment
uv sync --group dev

# run tests
uv run pytest

# run litmus against itself (yes, we eat our own dogfood)
uv run litmus verify
```

requirements: **python 3.11+**, `uv`, and git (matches `requires-python` in `pyproject.toml`).

---

<a name="architecture"></a>
## architecture at a glance

the Python package lives under `src/litmus/`. today’s layout (evolving):

```
src/litmus/
├── main.py, cli.py          # entrypoint + typer commands
├── config.py, watch.py
├── discovery/               # diff, ASGI app + project detection, routes, tracing
├── dst/                     # deterministic runtime, scheduler, ASGI harness, faults, engine
├── invariants/              # models, store, mined tests, LLM suggestions
├── scenarios/               # scenario builder
├── properties/              # property-based checks
├── replay/                  # differential replay + trace types
├── simulators/              # httpx, aiohttp, http, sqlalchemy async, redis async
└── reporting/               # console, PR comment, confidence scoring
```

the three things to understand:

1. **simulators** intercept I/O libraries via monkey-patching. they implement enough behavior to exercise real application code and inject faults on command. they are deterministic — same seed, same result, always.

2. **layers** are the three verification stages: invariants + property tests, dst, differential replay. each layer is independent and reports its own results. discovery + dst engine code orchestrates them.

3. **discovery + dst** parse the diff, trace affected endpoints, build scenarios, patch the runtime, import the ASGI app, and run the verification stack. that's the glue.

---

<a name="what-to-work-on"></a>
## what to work on

### high impact

**simulation adapters.** this is where contributions matter most. every new adapter expands the stack litmus supports zero-config. see [writing a simulation adapter](#writing-a-simulation-adapter) below.

adapters we want:

- `celery` — task queue simulation with retry/failure injection
- `boto3` / `aiobotocore` — aws service simulation (s3, sqs, dynamodb)
- `motor` — mongodb async driver
- `grpclib` / `grpcio` — grpc client simulation
- `nats-py` — nats messaging
- `pika` / `aio-pika` — rabbitmq

**invariant packs.** reusable sets of invariants for common patterns. see [writing an invariant pack](#writing-an-invariant-pack).

packs we want:

- `payments` — idempotency, double-charge prevention, refund consistency
- `queues` — at-least-once delivery, ordering, dead letter handling
- `auth` — session expiry, token refresh, permission escalation
- `pagination` — cursor stability, total count consistency, empty page handling

### medium impact

- **fault types.** new fault injection patterns for the dst engine (dns failures, tls errors, connection resets mid-body, slow drip responses).
- **framework detection.** improve ASGI app discovery for non-standard project layouts, django asgi, quart, litestar.
- **test mining.** better extraction of input/output pairs from complex pytest fixtures, parametrized tests, conftest setups.

### always welcome

- bug reports with a reproducible seed or minimal reproduction
- documentation improvements
- typo fixes (yes, really)

### not right now

- typescript / node support (we're building this internally, coordination needed)
- web dashboard (not started yet)
- mcp server (design phase)

if you want to work on something not listed here, open an issue first so we can align.

---

<a name="writing-a-simulation-adapter"></a>
## writing a simulation adapter

this is the most impactful contribution you can make. a good adapter means litmus works zero-config for every project using that library.

### the interface

every simulator implements `BaseSimulator`:

```python
from litmus.simulators.base import BaseSimulator, FaultSpec

class MyLibrarySimulator(BaseSimulator):
    """semantic simulator for my-library."""

    # which module to patch
    target_module: str = "my_library"

    def install(self) -> None:
        """monkey-patch the target module.

        called once before user code is imported.
        replace the real client/connection classes with
        simulated versions that route through self.
        """
        ...

    def inject_fault(self, fault: FaultSpec) -> None:
        """register a fault to trigger on the next matching operation.

        faults are consumed once triggered. the dst loop
        calls this before each await point based on the
        seed's fault schedule.
        """
        ...

    def checkpoint(self) -> dict:
        """capture current state for invariant checking.

        returns a serializable snapshot of all simulated state
        (tables, keys, pending operations, connection pool status).
        """
        ...

    def restore(self, checkpoint: dict) -> None:
        """restore to a previous state.

        used for differential comparison and replay.
        """
        ...

    def reset(self) -> None:
        """clear all state between scenarios.

        called between seeds to ensure isolation.
        """
        ...
```

### what "semantic simulator" means

you're not reimplementing the library. you're implementing the subset of behavior that application code relies on, with injectable faults.

for a database simulator, that means:

- basic CRUD operations against in-memory dictionaries
- transaction boundaries (begin/commit/rollback)
- connection lifecycle
- faults: connection drop, commit timeout, pool exhaustion

it does NOT mean: query optimization, complex joins, indexing, replication.

for an http client simulator, that means:

- configurable responses per URL pattern
- request/response capture
- faults: timeout, connection refused, 500, slow response

it does NOT mean: actual http parsing, tls, connection pooling internals.

**the rule: simulate what the application sees, not what the library does internally.**

### testing your adapter

```bash
# every adapter needs these test categories:

# 1. basic operations work
pytest tests/simulators/test_my_library.py::test_basic_ops

# 2. faults inject correctly
pytest tests/simulators/test_my_library.py::test_fault_injection

# 3. state checkpointing is correct
pytest tests/simulators/test_my_library.py::test_checkpoint_restore

# 4. determinism — same seed produces same trace
pytest tests/simulators/test_my_library.py::test_determinism

# 5. integration — run against a sample app that uses the library
pytest tests/simulators/test_my_library.py::test_sample_app
```

include a sample fastapi app in `tests/fixtures/apps/` that uses your library in a realistic pattern. this is how we verify the adapter works end-to-end.

### adapter checklist

before submitting:

- [ ] implements all `BaseSimulator` methods
- [ ] handles the 5-10 most common operations for the library
- [ ] supports at least 3 fault types relevant to the library
- [ ] deterministic — same seed, same result, always
- [ ] checkpointing captures all mutable state
- [ ] reset fully clears state between seeds
- [ ] tested with a realistic sample app
- [ ] documented: what it simulates, what it doesn't, known gaps

---

<a name="writing-an-invariant-pack"></a>
## writing an invariant pack

invariant packs are reusable `.yaml` files that encode domain-specific verification properties.

```yaml
# src/litmus/invariants/packs/payments.yaml  (illustrative path)
pack: payments
description: invariants for payment processing endpoints
version: 0.1.0

invariants:
  - name: charge_idempotency
    type: property
    description: >
      retrying a charge with the same idempotency key
      returns the same response without processing twice.
    applies_when:
      - endpoint_matches: "*/charge*"
      - method: POST
    severity: critical

  - name: refund_bounded_by_charge
    type: state_transition
    description: >
      refund amount cannot exceed original charge amount.
    applies_when:
      - endpoint_matches: "*/refund*"
    severity: critical

  - name: no_negative_balance
    type: invariant
    description: >
      account balance never goes negative after any
      combination of charges and refunds.
    severity: critical
```

**`applies_when`** defines when litmus should suggest this invariant. if the user's codebase has endpoints matching the pattern, these invariants are proposed as `suggested`.

**pack checklist:**

- [ ] each invariant has a clear `description` that explains the property in plain language
- [ ] `applies_when` is specific enough to avoid false matches
- [ ] `severity` is set correctly (critical = would cause data loss or financial impact, warning = correctness issue, info = best practice)
- [ ] the pack covers the 5-10 most important invariants for the domain, not every possible one

---

<a name="testing"></a>
## testing your changes

```bash
# run the full test suite
pytest

# run with coverage
pytest --cov=litmus

# run only simulator tests
pytest tests/simulators/

# run only dst tests
pytest tests/unit/dst/

# run litmus on the sample apps (integration)
pytest tests/integration/

# type checking (when mypy is configured for the repo)
mypy src/litmus/

# linting (when ruff is configured for the repo)
ruff check src/litmus/
```

all tests must pass before submitting a pr. ci runs the same suite.

---

<a name="submitting-a-pr"></a>
## submitting a pr

1. fork the repo and create a branch from `main`
2. make your changes
3. add or update tests
4. run `pytest` and `ruff check` locally
5. write a clear pr description: what you changed, why, and how to test it
6. if adding a simulator adapter, include the sample app in `tests/fixtures/apps/`

### pr review

we review for:

- **correctness** — does the change do what it says? are edge cases handled?
- **determinism** — if it touches the simulation or dst path, is it deterministic? same seed, same result?
- **simplicity** — is this the simplest way to achieve the goal? litmus is early; we prefer clear code over clever code.
- **test coverage** — is the change tested? for simulators: basic ops, faults, checkpointing, determinism, integration.

we don't review for:

- pedantic style nits (ruff handles this)
- perfect commit history (we squash merge)

we aim to review prs within 48 hours. if it's been longer, ping in discord.

---

<a name="code-style"></a>
## code style

- **ruff** for linting and formatting. run `ruff check --fix` and `ruff format` before committing.
- **mypy** for type checking. all public functions have type annotations.
- **docstrings** on all public classes and functions. plain language, no jargon.
- **no abbreviations** in variable names unless they're universal (`id`, `url`, `db`).
- **comments explain why, not what.** the code explains what.

---

<a name="reporting-bugs"></a>
## reporting bugs

the best bug report includes a reproducible seed.

```
litmus version: 0.1.0
python version: 3.11.4
stack: fastapi 0.110.0, httpx 0.27.0, sqlalchemy 2.0.30

what happened:
  litmus verify reports a false positive on seed 1234.
  the invariant `charge_returns_200_on_success` fails,
  but the endpoint returns 200 correctly.

to reproduce:
  litmus replay seed:1234

expected:
  seed 1234 should pass.
```

if you can't get a seed, a minimal reproduction (a small fastapi app + the litmus command that triggers the issue) is the next best thing.

open a [github issue](https://github.com/rajat1299/litmus/issues/new) with the above template.

---

<a name="community"></a>
## community

- **discord** — [discord.gg/litmus](https://discord.gg/litmus) for questions, discussion, and showing off what you've built
- **github issues** — for bugs and feature requests
- **github discussions** — for design conversations and rfcs

---

## license

by contributing to litmus, you agree that your contributions will be licensed under the [mit license](LICENSE).
