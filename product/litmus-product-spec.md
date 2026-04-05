# Litmus — Product Spec v0.2

> Deterministic fault-injection verification for agent-written code.

**Author:** Rajat
**Date:** March 29, 2026
**Status:** Locked Design Decisions — Pre-Development
**Confidentiality:** Internal

---

## Framing Note

This document is the locked product design target, not the shipped alpha truth surface.

For the currently shipped repository surface, use:

- `docs/alpha-quickstart.md`
- `docs/releases/2026-03-31-alpha.md`
- CLI help from `litmus --help`
- local MCP tool descriptions from `litmus mcp`

## Locked Decisions (Summary)

These decisions are finalized and inform every section of this spec.

| Decision | Locked Choice |
|----------|---------------|
| Product approach | DST-first local-to-team |
| Acquisition hook | `litmus watch` (solo dev in-editor) |
| Conversion path | GitHub Action + PR comment (team) |
| Hero capability | Zero-config DST with fault injection |
| Supporting layers | Invariants + property tests, differential replay |
| GTM sequence | Solo dev acquisition → small team monetization |
| First canonical workload | Python async services (FastAPI/Starlette on asyncio) |
| Supported launch adapters | asyncio, httpx, aiohttp, sqlalchemy.ext.asyncio, redis.asyncio |
| Integration model | Zero-config monkey-patching, no SDK, no `import litmus` |
| Execution model | In-process ASGI invocation inside a pre-patched deterministic runtime |
| Default verification unit | Changed request flows / endpoints (functions + tests as inputs) |
| Invariant sourcing | Hybrid: mined tests as anchor, LLM extends with suggested invariants |
| External state model | Semantic simulators (in-memory) for sqlalchemy, redis, httpx |
| Unsupported stack behavior | Graceful degradation to non-DST verification |
| Second workload (fast-follow) | TypeScript Node services (fetch + prisma/pg + ioredis) |

---

## 1. Why This Exists

AI coding agents produce code faster than any team can verify it. The bottleneck has moved from writing code to trusting what was written.

The current landscape:

- **AI coding tools** (Cursor, Claude Code, Copilot) focus on making agents write faster
- **AI testing tools** (Tusk, testRigor, Virtuoso) focus on generating UI/E2E tests
- **Antithesis** does DST but is enterprise-only, not self-serve, requires Docker containers uploaded to their infrastructure, and is not optimized for the agent-generated code workflow
- **Code review tools** (Graphite, GitHub) still treat review as the primary correctness gate

The gap: nobody has productized deterministic simulation testing as a developer-facing CLI for verifying agent-generated code. The technique exists (FoundationDB, TigerBeetle, Antithesis). The need is acute (production incidents from AI-generated code up 43% YoY). The product doesn't exist.

Litmus fills this gap. It's a CLI-first tool that sits between your AI coding agent and deployment. When an agent generates code, Litmus runs deterministic simulation testing with fault injection, checks invariants, replays against existing behavior, and gives you a verification verdict — in under 10 seconds, with zero code changes required.

**Core thesis:** A good harness makes iteration cheap. A weak harness cannot be compensated for by better models or more human review. Litmus is the harness-as-a-product.

---

## 2. Product Vision

### One-Liner

Deterministic fault-injection verification for agent-written code.

### Elevator Pitch

Litmus is what you run after your AI agent writes code and before you ship it. It catches the bugs that agents produce most and code review misses entirely: race conditions under cascading timeouts, partial failures that corrupt state, retry logic that double-processes. It does this through deterministic simulation testing — injecting faults into your async I/O, replaying with seeds that make every failure reproducible, and checking invariants at each step. Zero config on FastAPI + httpx + sqlalchemy + redis. Under 10 seconds. Free for solo devs. GitHub Action for teams.

### Product Principles

1. **DST is the hero.** Every other feature supports the narrative that Litmus catches bugs nothing else can find. Invariants and property tests are valuable but they don't carry the story alone.
2. **Seconds, not hours.** The local verification loop stays under 10 seconds. If it's slower than the agent, nobody waits.
3. **Zero config on the supported stack.** No SDK. No imports. No decorators. `litmus verify` on a standard FastAPI project works out of the box.
4. **Agent-native.** The feedback loop goes back to the agent, not to a reviewer's inbox. The hero loop is: agent writes → Litmus finds failure seed → agent fixes → Litmus passes.
5. **Honest degradation.** If the stack isn't fully supported, say so clearly and run what you can. Never fake confidence.

---

## 3. Target Users & GTM

### GTM Sequence

**Solo devs are the acquisition channel. Small teams are the paying customer.**

Solo devs discover Litmus because it works in their editor workflow (`litmus watch` alongside Cursor/Claude Code). They install it, it catches a bug, they tweet about it. The team lead discovers it because their dev is already using it and says "we should add this to CI." The team lead pays $25/user/month for the GitHub Action and PR comments.

This is the Graphite path: individual dev adopts CLI → brings it to team → team pays.

### Persona 1: Solo Dev — "Vibe Coder" (Acquisition)

- Uses Cursor, Claude Code, or Copilot daily on Python async services
- Ships agent-generated code with minimal review
- Pain: "I shipped an agent-generated retry handler that looked right but double-processed payments under cascading timeouts. Cost me $2,000 and 3 hours of debugging."
- Hook: `litmus watch` catches the bug in 5 seconds while the agent is still writing
- Conversion: tells their team lead about it

### Persona 2: Small Team Lead — "Shipping Squad" (Monetization)

- 3-10 person team, moving fast, multiple devs using AI agents
- Code review can't keep up with agent-generated PR volume
- Pain: "We review 40 PRs a day now. Half are agent-generated. We're rubber-stamping."
- Hook: GitHub Action with PR comments showing verification verdicts
- Conversion: pays $25/user/month for CI verification + team features

### Persona 3: Platform Engineer (v1.0, Not Launch)

- Works at a 50-500 person org, responsible for CI/CD and code quality
- Pain: "Management wants us to adopt Cursor for everyone. I need to prove it won't increase incidents."
- Needs: Dashboard, confidence trends, policy controls, observability integration
- These features ship post-launch. This persona is the enterprise expansion, not the wedge.

---

## 4. Form Factor

### CLI-First + Cloud Backend

**Local experience (acquisition):**
- `litmus init` — detects ASGI app, analyzes codebase, mines tests, generates initial invariants
- `litmus verify` — runs full verification pyramid against staged changes
- `litmus watch` — continuous verification on file save, designed to pair with AI coding agents
- `litmus replay <seed>` — deterministic replay of a failing DST seed

**Cloud experience (conversion):**
- GitHub Action — runs on every PR as a check
- PR comment — detailed verification report posted inline (this IS the dashboard for v0.1)
- Required check — teams can block merges below a confidence threshold

**What does NOT ship at launch:**
- Web dashboard (the PR comment replaces this for early teams)
- Team invariant sharing (post-launch)
- Observability integrations (post-launch)
- MCP server for agent integration (post-launch, high value)

---

## 5. The Verification Pyramid

Three layers ship complete at launch. DST is the hero. Invariants + property tests and differential replay make the verdict stronger but do not carry the narrative.

### Layer 1: Invariants + Property Tests (< 3 seconds)

**What:** Automatically generated invariants checked via property-based testing with randomized inputs.

**Invariant sourcing (hybrid):**

Step 1 — Mine existing tests and fixtures into a baseline behavior contract. These are auto-confirmed. The developer already stated this intent.

Step 2 — LLM analyzes the diff + code context and proposes additional invariants around changed code. These are suggested, pending review.

Step 3 — Surface the gap between what tests cover and what the code implies. This gap is where the bugs live and where the product delivers value.

```yaml
# .litmus/invariants/payment_service.yaml

# Mined from tests (auto-confirmed)
- name: charge_returns_200_on_success
  source: mined:tests/test_payment.py::test_charge_success
  status: confirmed
  type: differential

- name: charge_returns_402_on_insufficient_funds
  source: mined:tests/test_payment.py::test_charge_nsf
  status: confirmed
  type: differential

# LLM-generated (suggested, pending review)
- name: charge_is_idempotent_on_retry
  source: llm:diff_analysis
  status: suggested
  type: property
  reasoning: >
    Retry logic in lines 42-58 re-calls charge() on timeout,
    but no deduplication key is passed. If the first call succeeded
    before the timeout, this produces a double charge.

- name: charge_rollback_on_partial_failure
  source: llm:code_context
  status: suggested
  type: state_transition
  reasoning: >
    Database write at line 67 follows the API call at line 54.
    If the DB write fails, the charge is not reversed.
```

**Property testing:** For each invariant, Litmus generates property-based tests using Hypothesis (Python). Tests run with configurable iteration count (default: 100 local, 1000 CI). Failing inputs are shrunk to minimal reproductions.

**Property types:**
- Roundtrip: `decode(encode(x)) == x`
- Metamorphic: `sort(shuffle(xs)) == sort(xs)`
- Differential: `new_impl(x) == reference_impl(x)` for sampled inputs
- Invariant: `for all x: property(f(x))`

### Layer 2: Deterministic Simulation Testing (< 10 seconds) — HERO

**What:** Deterministic execution of affected endpoints with fault injection across all I/O boundaries. Catches race conditions, partial failures, state corruption, and retry bugs that code review and unit tests miss.

**How it works:**

```
litmus verify
    │
    ▼
1. Parse diff → identify changed functions
    │
    ▼
2. Trace changed functions → affected endpoints
   (parse FastAPI/Starlette route decorators)
    │
    ▼
3. Build scenarios per endpoint:
   - Mined from existing tests (confirmed)
   - Generated by LLM (suggested)
   - Includes: request shape, expected behavior, edge cases
    │
    ▼
4. Build patched deterministic runtime:
   - Replace asyncio event loop with Litmus's simulated loop
   - Patch httpx → semantic HTTP simulator
   - Patch sqlalchemy.ext.asyncio → semantic DB simulator
   - Patch redis.asyncio → semantic Redis simulator
   - Patch aiohttp → semantic HTTP simulator
   - Seed PRNG for deterministic execution
    │
    ▼
5. Detect and import ASGI app inside patched runtime:
   - Check litmus.yaml for explicit app path
   - Check pyproject.toml / uvicorn config
   - Scan for FastAPI() / Starlette() instantiation
   - Fallback: prompt developer to configure
    │
    ▼
6. For each scenario × seed:
   - Build ASGI scope (method, path, headers, body)
   - Call app(scope, receive, send) in-process
   - At each await point: consult fault schedule for this seed
     → inject: timeout, connection drop, slow response,
        500 error, partial write, pool exhaustion, OOM
   - Capture response + simulator state
   - Check invariants against response + state
    │
    ▼
7. Report results per endpoint with seed-level detail
```

**Semantic simulators:**

These are not databases. They are deterministic state machines that implement the subset of behavior application code actually touches.

**sqlalchemy async simulator:**
- `INSERT` / `SELECT` / `UPDATE` / `DELETE` against in-memory dictionaries keyed by table + primary key
- Transaction boundaries: `BEGIN` / `COMMIT` / `ROLLBACK` with read-committed isolation
- Connection lifecycle: `connect` / `close` / pool behavior
- Schema introspected from sqlalchemy ORM metadata at import time (no manual config)
- Faults: connection drop mid-transaction, commit timeout, pool exhaustion, deadlock on concurrent writes
- Does NOT simulate: query optimization, complex joins, migrations, indexes, full SQL parsing

**redis async simulator:**
- String ops: `GET` / `SET` / `SETEX` / `INCR` / `DEL`
- Hash ops: `HGET` / `HSET` / `HGETALL`
- List ops: `LPUSH` / `RPUSH` / `LPOP` / `BRPOP` (with simulated blocking)
- Pub/sub: `PUBLISH` / `SUBSCRIBE` (delivered through simulated event loop)
- Key expiry: deterministic based on simulated time
- Faults: connection refused, timeout on `BRPOP`, partial write, cluster MOVED errors

**httpx / aiohttp simulator:**
- Returns configurable responses per URL pattern (status, headers, body, latency)
- Default: 200 with empty body (unknown external calls don't crash)
- LLM generates realistic response fixtures based on URL patterns in the code
- Faults: timeout, connection refused, 500, slow response, partial response, DNS failure

**Fault injection profiles:**
- **Gentle:** 5% failure rate, minor delays — catches basic error handling
- **Hostile:** 30% failure rate, cascading failures — catches retry/recovery bugs
- **Chaos:** 60% failure rate, byzantine behavior — catches edge-case timing

**Seed count defaults:**
- Local (`litmus verify`): 100 seeds per scenario
- CI (GitHub Action): 500 seeds per scenario
- Configurable via `litmus config set dst.seeds <N>`

**Deterministic replay:**
Every failing seed is reproducible. `litmus replay seed:3847` replays the exact execution — same PRNG sequence, same fault schedule, same order of operations. The developer sees the full trace: which request was being processed, which await point was reached, which fault was injected, what state was corrupted.

### Layer 3: Differential Replay (< 3 seconds)

**What:** Replay existing test fixtures and captured scenarios against the changed code. Compare outputs to the baseline. Flag divergences.

**How it works:**
1. Mine input/output pairs from existing pytest fixtures and test cases
2. Run the same inputs against the changed code
3. Compare outputs — any divergence is flagged with a diff
4. Classify divergences: breaking change, benign change, or improvement

**This layer catches regressions.** It doesn't find new bugs — DST does that. Differential replay ensures the changed code doesn't break what already worked.

---

## 6. The Confidence Score

Each verification run produces a confidence score (0-100) aggregated across all three layers:

```
LITMUS VERIFICATION REPORT
═══════════════════════════════════════════════
Commit: a1b2c3d (feat: add retry logic to payment service)
Agent: Claude Code via Cursor

Score: 87/100 ██████████████████░░ HIGH CONFIDENCE

Affected endpoints: 2
  POST /payments/charge  (via retry_charge)
  POST /payments/refund  (via retry_charge)

Layer 1 — Invariants + Properties:
  ✅ 12 invariants (8 confirmed, 4 suggested)
  ✅ 847/847 property checks passed

Layer 2 — DST:
  ⚠️ 498/500 seeds passed for POST /payments/charge
     2 seeds failed: double charge under cascading timeout
     → litmus replay seed:3847
     → litmus replay seed:4102
  ✅ 500/500 seeds passed for POST /payments/refund

Layer 3 — Differential Replay:
  ✅ 100% output match on 23 mined test fixtures

Recommendation: REVIEW DST FAILURES before merging.
  Seeds 3847 and 4102 show that when httpx times out on the
  first charge attempt and the retry succeeds, no deduplication
  check prevents the original (late-arriving) success from also
  being recorded. Both calls return 200. The customer is charged
  twice.

Time: 8.3 seconds
═══════════════════════════════════════════════
```

The confidence score is calibrated to under-report, not over-report. Zero false positives is the trust contract. If DST fails, there is a real bug.

---

## 7. CLI Reference

### Installation

```bash
# pip (primary distribution for Python-first launch)
pip install litmus-cli

# homebrew
brew install litmus

# npm (for TypeScript fast-follow)
npm install -g @litmus/cli
```

### Core Commands

```bash
# Initialize — detect app, analyze codebase, mine tests, generate invariants
litmus init
# → Detects FastAPI/Starlette app entry point
# → Mines existing tests into confirmed invariants
# → Generates suggested invariants via LLM
# → Writes .litmus/ directory

# Run full verification pyramid on staged changes
litmus verify
# → Layer 1: Invariants + property tests (~3s)
# → Layer 2: DST with fault injection (~5-10s)
# → Layer 3: Differential replay (~3s)
# → Outputs confidence score
# → Exits non-zero on critical failures

# Verify specific file or directory
litmus verify src/services/payment.py

# Watch mode — re-verify on every file save
# Designed to run alongside AI coding agents in-editor
litmus watch

# Replay a failing DST seed with full execution trace
litmus replay seed:3847

# View/edit invariants
litmus invariants list
litmus invariants edit src/services/payment_service.yaml

# Configure
litmus config set dst.seeds 500
litmus config set dst.fault-profile hostile   # gentle | hostile | chaos
litmus config set app "src.main:app"          # explicit ASGI app path
```

### CI Integration (GitHub Action)

```yaml
# .github/workflows/litmus.yml
name: Litmus Verification
on: [pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: rajat1299/litmus@v1
        with:
          token: ${{ secrets.LITMUS_TOKEN }}
          mode: ci                # 500 seeds instead of 100
          min-score: 80           # fail PR if below threshold
          comment: true           # post results as PR comment
```

The PR comment IS the team-facing artifact at launch. No dashboard needed. The comment contains: confidence score, affected endpoints, layer results, failing seeds with reproduction commands, and a human-readable explanation of what went wrong.

### Agent Integration (Post-Launch)

MCP server for direct integration with Claude Code, Cursor, and MCP-compatible agents:

```bash
# Start Litmus as an MCP server
litmus mcp serve

# Agent can call:
# - litmus.verify()
# - litmus.replay(seed)
# - litmus.explain(failure)
# - litmus.invariants.list()
```

This closes the loop: agent writes code → calls `litmus.verify()` → receives structured failure data → fixes the issue → calls verify again → passes. The agent never leaves the loop. This is the "agent-native" workflow that makes Litmus fundamentally different from tools designed for human review. Ships post-launch but is the highest-value follow-up feature.

---

## 8. Integration Model

### Zero-Config Patching (v0.1)

**No `import litmus` required.** The developer's code doesn't change.

`litmus verify` spawns the target code in a subprocess where Litmus has already monkey-patched the supported libraries at the module level before the user's code imports them. This is the same pattern pytest-asyncio, responses, moto, and time-machine use.

```
litmus verify src/services/payment.py
    │
    ▼
1. Litmus pre-loads simulation adapters
2. Patches: httpx.AsyncClient, sqlalchemy.ext.asyncio,
   redis.asyncio, aiohttp.ClientSession, asyncio event loop
3. Imports ASGI app inside patched environment
4. Invokes affected endpoints in-process via ASGI protocol
5. Injects faults per seed schedule at each await point
6. Checks invariants at each step
7. Reports results
```

**Supported launch stack (zero-config DST):**
- Runtime: `asyncio` (Python 3.10+)
- HTTP clients: `httpx`, `aiohttp`
- Database: `sqlalchemy.ext.asyncio`
- Cache/queue: `redis.asyncio`
- Frameworks: `FastAPI`, `Starlette` (auto-detected)

**Unsupported stack behavior:**

If Litmus detects I/O boundaries it can't simulate (proprietary SDKs, custom HTTP clients, non-standard libraries), it degrades honestly:

```
⚠️ DST partially available.
   Detected: httpx ✅ sqlalchemy ✅ stripe-python ❌ (unsupported)
   
   Layer 1 (Invariants + Properties): running ✅
   Layer 2 (DST): running for httpx + sqlalchemy boundaries only.
                   stripe-python calls will pass through unsimulated.
   Layer 3 (Differential Replay): running ✅
   
   To enable full DST for stripe-python, add boundary markers:
   → litmus docs boundary-markers
```

### Boundary Markers (Post-Launch, Opt-In)

For unsupported libraries, developers can add lightweight annotations:

```python
from litmus import boundary

@boundary.external("payment_provider")
async def charge_card(card_id: str, amount: int):
    return await stripe.charges.create(card_id, amount)
```

This is not an SDK. It's a single decorator that tells Litmus "this is an external I/O boundary, simulate it." Ships post-launch only.

---

## 9. Execution Model

### In-Process ASGI Invocation

Litmus imports the ASGI app and calls endpoints via the standard ASGI interface (`app(scope, receive, send)`). No real server, no real ports, no network.

**Why this model:**
- Deterministic: the asyncio event loop is Litmus's simulated loop. Every `await` is a controlled yield point.
- Fast: no server boot, no connection overhead, no port conflicts.
- Full control: Litmus controls fault injection timing at each await point.

**App discovery (in order):**
1. `litmus.yaml` → explicit `app: "src.main:app"`
2. `pyproject.toml` / uvicorn config → infer app path
3. AST scan for `FastAPI()` / `Starlette()` instantiation in common locations
4. Fallback: prompt developer → `litmus init --app src.main:app`

**Non-ASGI fallback:**
For plain asyncio services without a web framework, Litmus falls back to changed-functions-as-verification-unit. DST still runs at the function level with fault injection on I/O calls. The endpoint-level reporting and scenario generation are framework-specific; the underlying DST engine is not.

---

## 10. Performance Budget

```
Simulator init (import app + build in-memory state):    ~500ms
Invariant check + property tests (Layer 1):             ~2,000ms
Per-DST-seed execution (scenario + faults + checks):    ~50ms
100 seeds (local default):                              ~5,000ms
Differential replay (Layer 3):                          ~1,500ms
────────────────────────────────────────────────────────
Total local verification:                               ~9,000ms (< 10s)

CI mode (500 seeds):                                    ~27,000ms (< 30s)
```

The 10-second local loop is a hard constraint. If any component threatens it, that component runs async or gets cut from the local path and moves to CI-only.

---

## 11. Pricing

### Hobby (Free)

For solo devs and personal projects.

- Personal repos only
- Full local CLI with all three verification layers
- 100 CI verification runs/month
- 100 DST seeds per run (local and CI)
- Community invariant packs
- GitHub PR checks + comments

### Starter ($25/user/month, billed annually)

For small teams shipping production code.

- Everything in Hobby
- All org repos
- 1,000 CI verification runs/month
- 500 DST seeds per run
- Slack/Discord notifications
- Team invariant sharing
- PR-level confidence trends

### Team ($50/user/month, billed annually)

For growing teams that need deep verification coverage.

- Everything in Starter
- Unlimited CI verification runs
- 5,000 DST seeds per run
- Custom fault injection profiles
- MCP server for agent integration
- Observability integrations (Datadog, Grafana)
- Priority support

### Enterprise (Custom)

- Everything in Team
- Self-hosted option
- SSO/SAML, audit logs
- Dedicated simulation infrastructure
- SLA + premium support, SOC 2

---

## 12. Competitive Positioning

### vs. Antithesis

Antithesis is the gold standard for DST but is enterprise-only, not self-serve, and requires uploading your entire system as Docker containers. Litmus is self-serve, CLI-first, runs locally, and is purpose-built for the agent-generated code workflow. Antithesis finds bugs in your existing system. Litmus verifies agent-generated changes before they reach your system.

"Antithesis is the MRI machine. Litmus is the daily health check."

### vs. AI Testing Tools (Tusk, testRigor, etc.)

They generate tests (unit, E2E, UI). Litmus generates verification — deterministic simulation with fault injection. Tests ask "does this input produce this output?" Verification asks "does this code survive cascading failure?" The distinction matters when agents generate code that passes all tests but fails under production fault conditions.

"They generate tests. We generate trust."

### vs. Graphite / GitHub Code Review

Graphite optimizes the review workflow. Litmus replaces review as the primary correctness gate for agent-generated code. Complementary: Graphite for human review, Litmus for automated verification.

"Graphite is how your team reviews. Litmus is how your team verifies."

### vs. Static Analysis (SonarQube, CodeClimate)

Static analysis checks code style and known patterns. It doesn't check behavioral correctness under fault conditions. A function that handles every linter rule perfectly can still double-charge customers under a cascading timeout.

"Static analysis tells you the code looks right. Litmus tells you the code survives."

---

## 13. Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DEVELOPER MACHINE                       │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ AI Agent │───▶│ Code Changes │───▶│   litmus watch     │  │
│  │ (Cursor, │    │              │    │                      │  │
│  │  Claude  │    │              │    │  ┌────────────────┐  │  │
│  │  Code)   │◀───│              │◀───│  │ Verify Engine  │  │  │
│  └──────────┘    └──────────────┘    │  │                │  │  │
│   (reads failure                     │  │ 1. Diff parse  │  │  │
│    + fixes)                          │  │ 2. Endpoint    │  │  │
│                                      │  │    trace       │  │  │
│                                      │  │ 3. Scenario    │  │  │
│                                      │  │    build       │  │  │
│                                      │  │ 4. Patch       │  │  │
│                                      │  │    runtime     │  │  │
│                                      │  │ 5. Import ASGI │  │  │
│                                      │  │ 6. DST loop    │  │  │
│                                      │  │ 7. Report      │  │  │
│                                      │  └────────────────┘  │  │
│                                      └──────────┬───────────┘  │
└─────────────────────────────────────────────────┼──────────────┘
                                                  │
                                           (sync to cloud
                                            if connected)
                                                  │
┌─────────────────────────────────────────────────┼──────────────┐
│                       LITMUS CLOUD             ▼              │
│                                                                 │
│  ┌────────────────────┐    ┌──────────────────────────────┐    │
│  │ GitHub App         │    │ Verification Orchestrator    │    │
│  │ - PR check status  │    │ - CI-mode DST (500 seeds)   │    │
│  │ - PR comment with  │    │ - Invariant store            │    │
│  │   full report      │    │ - Result aggregation         │    │
│  │ - Required check   │    │                              │    │
│  │   gate             │    │                              │    │
│  └────────────────────┘    └──────────────────────────────┘    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Post-Launch                                              │  │
│  │ - MCP server for agent integration                       │  │
│  │ - Web dashboard + confidence trends                      │  │
│  │ - Team invariant sharing                                 │  │
│  │ - Observability bridge (Datadog, Grafana)                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Technical Decisions

**DST engine:** Written in Python for v0.1 (same language as the target workload — simplifies patching and introspection). If performance becomes a constraint, the simulation loop can be rewritten in Rust with Python bindings for v1.0.

**Simulation adapters:** Each adapter implements a standard interface: `intercept()` (hook into library's I/O layer), `inject_fault(type, params)` (trigger simulated fault), `checkpoint_state()` (capture state for comparison), `restore_state(checkpoint)` (restore to previous state). Adapters are independent packages.

**LLM integration:** Used for invariant generation and scenario suggestion only. Never in the verification path. Verification is always deterministic and reproducible. Supports any OpenAI-compatible API, defaults to Claude.

**Invariant format:** YAML files in `.litmus/invariants/` with `status: confirmed | suggested` distinction. Confirmed invariants come from mined tests. Suggested invariants come from LLM analysis. Developers curate the set over time.

---

## 14. The Demo Script

This is the 60-second demo that ships with launch. It demonstrates the hero loop.

```
1. Open VS Code with a FastAPI payment service
2. Start litmus watch in terminal
3. Open Cursor, prompt: "Add retry logic to the charge endpoint 
   for when the payment provider times out"
4. Cursor writes the retry handler
5. litmus watch triggers automatically
6. Output appears in ~8 seconds:

   LITMUS — POST /payments/charge
   ⚠️ DST FAILURE — 2/100 seeds failed
   
   Seed 3847: httpx timeout on first charge attempt.
   Retry succeeds. But the original request completes
   late (slow, not failed). No deduplication.
   Result: customer charged twice.
   
   → litmus replay seed:3847

7. Developer reads the failure, tells Cursor: "Add idempotency 
   key to the charge retry logic"
8. Cursor fixes
9. litmus watch triggers again
10. Output: ✅ 100/100 seeds passed. Score: 94/100.
```

That's the tweet. That's the HN post. That's the product.

---

## 15. Risks & Mitigations

**Risk: Semantic simulators miss real database/Redis behavior.**
Mitigation: The simulators cover the 90% of application-level patterns (CRUD, transactions, caching). The 10% they miss (Postgres advisory locks, Redis Lua scripts) are documented honestly. Post-launch, add higher-fidelity simulators and opt-in live backend mode for users who need it.

**Risk: Monkey-patching breaks on edge-case library versions or unusual import patterns.**
Mitigation: Pin supported library versions at launch. Test against the 5 most common version combinations. When patching fails, degrade to non-DST verification with a clear error message.

**Risk: False positives erode trust.**
Mitigation: Conservative defaults. Zero false positives is the contract. If DST fails, there's a real bug — the seed proves it with a reproducible trace. Confidence scores under-report rather than over-report.

**Risk: Antithesis or Datadog ships this as a product.**
Mitigation: Antithesis targets full-system simulation, not the in-editor agent workflow. Datadog would build it as a Datadog feature, not a standalone CLI. Litmus's moat is the developer workflow: CLI, watch mode, agent feedback loop, zero-config patching. By the time incumbents move, Litmus has community and workflow lock-in.

**Risk: LLM-generated invariants produce noise.**
Mitigation: Mined-tests-as-anchor means the baseline is always grounded. LLM invariants are explicitly labeled `suggested` and never auto-enforced. The developer's job is to dismiss bad suggestions, not write invariants from scratch.

**Risk: App discovery fails on non-standard project structures.**
Mitigation: Four-step detection cascade (litmus.yaml → pyproject.toml → AST scan → prompt). Covers the common case automatically. Non-standard projects get a one-time `litmus init --app src.main:app` setup.

---

## 16. Success Metrics

### North Star

**Bugs caught per developer per week.** If Litmus isn't finding real bugs that would have shipped, it's not delivering value.

### Leading Indicators

| Metric | Signal | Target (3 months post-launch) |
|--------|--------|-------------------------------|
| CLI installs | Adoption | 5,000 |
| Weekly `litmus verify` runs | Engagement | 500 active weekly users |
| DST failures → code changes | Impact | 60%+ of DST failures lead to a fix |
| Invariants kept / generated | Quality | 70%+ mined invariants kept, 40%+ suggested kept |
| Time: agent output → verified | Speed | < 10 seconds median |

### Lagging Indicators

| Metric | Signal | Target (6 months post-launch) |
|--------|--------|-------------------------------|
| Paying teams | Revenue | 50 teams, $15K MRR |
| Incidents in Litmus repos vs. not | Impact | Measurable reduction |
| NPS among team leads | Satisfaction | 50+ |

---

## 17. Launch Roadmap

### v0.1 — Launch (Weeks 1-6)

All three verification layers, complete, for Python async on FastAPI/Starlette.

**Ships:**
- `litmus init` — app detection, test mining, invariant generation
- `litmus verify` — full pyramid (invariants + properties, DST, differential replay)
- `litmus watch` — continuous verification on file save
- `litmus replay <seed>` — deterministic failure replay
- Zero-config patching for asyncio, httpx, aiohttp, sqlalchemy.ext.asyncio, redis.asyncio
- Semantic simulators for all patched libraries
- In-process ASGI invocation with deterministic runtime
- Hybrid invariant sourcing (mined + LLM)
- Confidence score with endpoint-level reporting
- GitHub Action with PR comment
- `pip install litmus-cli`

**Does not ship:**
- TypeScript support
- MCP server
- Web dashboard
- Team invariant sharing
- Observability integrations
- Boundary markers for unsupported libraries

### v0.2 — TypeScript + MCP (Weeks 7-10)

- TypeScript Node services: fetch + prisma/pg + ioredis
- MCP server for Claude Code / Cursor integration
- Boundary markers (opt-in) for custom SDKs

### v0.3 — Team Features (Weeks 11-14)

- Web dashboard with confidence trends
- Team invariant sharing + community packs
- Slack/Discord notifications
- Observability bridge (Datadog, Grafana)

### v1.0 — Platform (Weeks 15-20)

- Enterprise features (SSO, audit, self-hosted)
- Custom fault profiles
- Formal specification checks (opt-in)
- Additional language support based on demand

---

## 18. Open Questions

1. **Name.** Product name is **Litmus** (litmus-test metaphor; memorable, lowercase-friendly CLI). Domain and packaging names still need final sign-off.

2. **Open-source scope.** CLI + local engine should be open-source (adoption). Cloud orchestrator + team features are the commercial moat.

3. **LLM provider.** Support any OpenAI-compatible API, default to Claude. Don't lock in.

4. **Invariant standard.** Opportunity to define an open format for code invariants that other tools adopt. If `.litmus/invariants/` becomes a standard, that's a massive moat.

5. **DST engine language.** Python for v0.1 (simplest, same ecosystem). Rust rewrite for v1.0 if performance demands it.

---

## Appendix A: References

- Datadog, "Harness-First Engineering" (2025) — foundational methodology
- Antithesis — DST platform, enterprise
- FoundationDB — pioneered simulation testing
- TigerBeetle — DST for financial systems
- Graphite — CLI-first dev tool model (product inspiration)
- Hypothesis — property-based testing for Python
- WarpStream — DST for Kafka-compatible streaming

## Appendix B: Name

**Chosen product name:** **Litmus** — litmus test as quick verification; memorable and fits a lowercase CLI.

Other candidates considered:

| Name | Metaphor | Notes |
|------|----------|-------|
| **Anvil** | Where things are forged/tested | Clean, may conflict with existing products |
| **Bastion** | Defensive fortification | Security connotation |
| **Lattice** | Interconnected structure | Technical, elegant |
| **Meridian** | Line of reference/truth | Unique, less obvious |
| **Sentinel** | Guardian/watcher | Overused in security space |
