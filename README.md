<p align="center">
  <br />
  <br />
  <img src="assets/litmus-logo.svg" alt="litmus" width="160" />
  <br />
  <br />
</p>

<h3 align="center">
  deterministic fault-injection verification<br/>for agent-written code.
</h3>

<p align="center">
  your ai agent writes code. litmus proves it survives.
</p>

<p align="center">
  <a href="#install">install</a> ·
  <a href="#how-it-works">how it works</a> ·
  <a href="#the-demo">the demo</a> ·
  <a href="#commands">commands</a> ·
  <a href="#ci">ci</a> ·
  <a href="#faq">faq</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/litmus-cli"><img src="https://img.shields.io/pypi/v/litmus-cli?style=flat-square&color=16a34a&labelColor=0a0a0a" alt="pypi" /></a>
  <a href="https://github.com/litmus-dev/litmus/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-16a34a?style=flat-square&labelColor=0a0a0a" alt="license" /></a>
  <a href="https://discord.gg/litmus"><img src="https://img.shields.io/badge/discord-join-16a34a?style=flat-square&labelColor=0a0a0a" alt="discord" /></a>
</p>

<br />

---

<br />

## the problem

ai agents produce code faster than you can review it. your tests pass. your linter is green. you ship.

then at 3am your retry logic double-charges a customer because both the original request and the retry succeeded under a cascading timeout. no test caught it. no reviewer saw it. the bug only exists in a specific failure timing that takes months to hit in production.

**litmus catches it in 5 seconds.**

<br />

## what litmus does

litmus runs your agent-written code through deterministic simulation testing with fault injection. it intercepts your async i/o — http calls, database transactions, redis operations — and systematically breaks things: timeouts, connection drops, partial writes, cascading failures. every run is seeded, so every failure is reproducible.

```
agent writes code → litmus verify → failure on seed 3847 → agent fixes → litmus passes
```

three verification layers, all under 10 seconds:

| layer | what it catches | time |
|-------|----------------|------|
| **invariants + property tests** | logic bugs, semantic drift, type violations | ~2s |
| **dst with fault injection** | race conditions, partial failures, retry bugs, state corruption | ~5s |
| **differential replay** | regressions against existing test behavior | ~2s |

<br />

## install

```bash
pip install litmus-cli
```

```bash
brew install litmus
```

<br />

## how it works

litmus needs zero code changes. no sdk. no imports. no decorators.

it monkey-patches your async libraries before your code imports them, runs your endpoints inside a deterministic simulation, and injects faults at every `await` point. same technique as pytest-asyncio, responses, and moto — nothing exotic.

**supported stack (zero-config):**

```
python 3.10+  ·  asyncio  ·  fastapi / starlette
httpx  ·  aiohttp  ·  sqlalchemy async  ·  redis-py async
```

if you're on this stack, `litmus verify` just works.

if litmus detects libraries it can't simulate, it tells you exactly what it can and can't verify — no silent gaps, no fake confidence.

<br />

<a name="the-demo"></a>
## the demo

```
 1.  cursor writes a retry handler for your payment endpoint
 2.  litmus watch triggers automatically

 ┌──────────────────────────────────────────────────────────────┐
 │                                                              │
 │  LITMUS — POST /payments/charge                              │
 │                                                              │
 │  ⚠ DST FAILURE — 2/100 seeds                                │
 │                                                              │
 │  seed 3847:                                                  │
 │    httpx timeout on first charge attempt.                    │
 │    retry succeeds. but the original request completes        │
 │    late — slow, not failed. no deduplication.                │
 │    result: customer charged twice.                           │
 │                                                              │
 │  → litmus replay seed:3847                                   │
 │                                                              │
 └──────────────────────────────────────────────────────────────┘

 3.  you tell cursor: "add an idempotency key"
 4.  cursor fixes
 5.  litmus watch triggers again

 ┌──────────────────────────────────────────────────────────────┐
 │                                                              │
 │  LITMUS — POST /payments/charge                              │
 │                                                              │
 │  ✓ 100/100 seeds passed                                     │
 │  score: 94/100                                               │
 │                                                              │
 └──────────────────────────────────────────────────────────────┘
```

<br />

<a name="commands"></a>
## commands

```bash
# initialize — detect app, mine tests, generate invariants
litmus init

# run full verification on staged changes
litmus verify

# verify a specific file
litmus verify src/services/payment.py

# watch mode — re-verify on every save
# designed to run alongside cursor, claude code, copilot
litmus watch

# replay a failing seed with full execution trace
litmus replay seed:3847

# view and manage invariants
litmus invariants list
litmus invariants edit payment_service.yaml

# configure
litmus config set dst.seeds 500
litmus config set dst.fault-profile hostile
```

**fault profiles:**

| profile | failure rate | what it finds |
|---------|-------------|---------------|
| `gentle` | 5% | basic error handling gaps |
| `hostile` | 30% | retry and recovery bugs |
| `chaos` | 60% | edge-case timing failures |

<br />

<a name="ci"></a>
## github action

```yaml
name: Litmus
on: [pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: litmus-dev/action@v1
        with:
          token: ${{ secrets.LITMUS_TOKEN }}
          mode: ci           # 500 seeds instead of 100
          min-score: 80      # block merge below threshold
          comment: true      # post results on the PR
```

the pr comment is the report. no dashboard required.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  litmus verification — a1b2c3d                               │
│  score: 87/100                                               │
│                                                              │
│  POST /payments/charge                                       │
│    invariants    ✓ 12/12                                     │
│    dst           ⚠ 498/500 seeds (2 failures)               │
│    replay        ✓ 23/23 fixtures                            │
│                                                              │
│  POST /payments/refund                                       │
│    invariants    ✓ 8/8                                       │
│    dst           ✓ 500/500 seeds                             │
│    replay        ✓ 11/11 fixtures                          │
│                                                              │
│  → litmus replay seed:3847                                   │
│  → litmus replay seed:4102                                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

<br />

## how invariants work

litmus generates invariants from two sources:

**mined from your tests** — what your code already promises, based on your own test fixtures. these are auto-confirmed. you wrote them.

**suggested by llm** — what your changed code implies but you didn't test for. these are marked `suggested` and you decide whether to keep them.

```yaml
# .litmus/invariants/payment_service.yaml

# mined (confirmed)
- name: charge_returns_200_on_success
  source: mined:tests/test_payment.py::test_charge_success
  status: confirmed

# llm-generated (suggested)
- name: charge_is_idempotent_on_retry
  source: llm:diff_analysis
  status: suggested
  reasoning: >
    retry logic in lines 42-58 re-calls charge() on timeout,
    but no deduplication key is passed.
```

the gap between what your tests cover and what your code implies is where the bugs live. litmus surfaces that gap.

<br />

## how dst works

litmus replaces your async runtime with a deterministic simulation:

1. **patches** asyncio, httpx, sqlalchemy, redis before your code imports them
2. **imports** your fastapi/starlette app in the patched environment
3. **invokes** affected endpoints via the asgi protocol (no real server, no ports)
4. **injects faults** at every `await` point: timeouts, drops, slow responses, partial writes
5. **checks invariants** against response + simulated state after each run
6. **seeds everything** — same seed = same execution = same result, always

semantic simulators replace your database and redis with deterministic in-memory state machines. they implement the subset of behavior your application code actually touches — transactions, connection lifecycle, key-value ops, pub/sub — with injectable faults at every boundary.

not a real database. a state machine that breaks on command.

<br />

<a name="faq"></a>
## faq

**does litmus require code changes?**
no. zero-config on the supported stack. no sdk, no imports, no decorators.

**what if my stack isn't fully supported?**
litmus tells you exactly which libraries it can and can't simulate. invariants and differential replay still run. dst runs for the boundaries it can simulate. no silent gaps.

**how is this different from antithesis?**
antithesis is enterprise-only, requires docker containers, and targets full-system simulation. litmus is self-serve, cli-first, runs locally, and is built for the agent-generated code workflow. antithesis is the mri. litmus is the daily health check.

**how is this different from pytest / hypothesis?**
pytest runs the tests you wrote. hypothesis generates test inputs. litmus generates fault schedules — it doesn't test your logic with different inputs, it tests your logic under different failure conditions. the bug litmus catches isn't "wrong output for input X" — it's "correct logic that corrupts state when the database drops mid-transaction."

**can my ai agent use litmus directly?**
mcp server support is coming. the agent will call `litmus.verify()`, receive structured failure data, fix the issue, and verify again — without leaving the loop.

**is litmus open source?**
the cli and local verification engine are open source (mit). cloud features (ci orchestration, team features) are commercial.

<br />

## roadmap

- [x] python async verification (fastapi + starlette)
- [x] zero-config dst with fault injection
- [x] invariant mining + llm generation
- [x] differential replay
- [x] github action + pr comments
- [ ] typescript node services
- [ ] mcp server for agent integration
- [ ] web dashboard
- [ ] team invariant sharing
- [ ] observability bridge (datadog, grafana)
- [ ] boundary markers for custom sdks
- [ ] formal specification checks

<br />

## contributing

litmus is open source and contributions are welcome. see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

the best way to contribute right now: simulation adapters for libraries we don't cover yet.

<br />

## license

mit — see [LICENSE](LICENSE)

<br />

---

<p align="center">
  <sub>litmus is built by <a href="https://github.com/litmus-dev">litmus-dev</a></sub>
  <br />
  <sub>the verification layer for agent-written code.</sub>
</p>
