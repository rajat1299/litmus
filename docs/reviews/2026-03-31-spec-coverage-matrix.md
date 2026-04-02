# Litmus Spec Coverage Matrix

**Status Date:** 2026-04-01  
**Repo State Reviewed:** `main` at `ecdc924`  
**References:** `product/litmus-product-spec.md`, top-level `README.md`, and the current shipped code/docs on `main`

## Purpose

This document answers a simple question: how much of the locked product spec and the aspirational top-level README is actually implemented in the repo today?

It is intentionally grounded in the current codebase, not in the broader product narrative.

## Status Legend

- **Implemented**: shipped in the current repo and usable end-to-end
- **Partial**: some supporting pieces exist, but the full promised workflow or contract does not
- **Not Implemented**: absent from the current shipped path
- **Out Of Scope For v0.1**: explicitly post-launch or otherwise outside the grounded alpha

## Executive Summary

- Litmus now has a **real tranche-one verification platform**: `init`, scoped `verify`, seeded main-path fault injection, run/activity artifacts, replay explanations, suggested invariant surfacing, GitHub Action/PR comments, and a local stdio MCP server all exist on `main`.
- Litmus still does **not** fully implement the complete v0.2 product spec or the broader top-level README surface.
- The biggest remaining gaps are:
  - the shipped DST hero path is still HTTP-first rather than a deeper multi-layer deterministic runtime
  - local verification depth is still below the broader spec targets (`3` replay seeds, not `100`; CI property depth is `500`, not `1000`)
  - suggested invariants are heuristic/curated and visible, but still lack a richer approval workflow
  - several broader CLI/config/install surfaces described in the README still do not exist (`invariants`, `config set`, Homebrew, public publish path)

## Matrix A: Product Spec Coverage

| Capability | Product Spec Expectation | Current Repo State | Status | Evidence |
| --- | --- | --- | --- | --- |
| Local CLI core | `litmus verify`, `litmus watch`, `litmus replay <seed>` ship at launch | These commands exist and are exercised by tests and demo docs | Implemented | `src/litmus/cli.py` |
| `litmus init` | Detect app, mine tests, generate invariants, write `.litmus/` | `init` now bootstraps config and invariant store, mines simple anchors, and reports support summary | Implemented | `src/litmus/init_flow.py`, `src/litmus/cli.py` |
| App discovery | Auto-detect ASGI app, allow explicit app config fallback | App discovery and explicit config support exist, and repeated in-process loads now observe on-disk app edits | Implemented | `src/litmus/discovery/app.py`, `src/litmus/config.py` |
| Mined invariants | Mine request/response fixtures from tests into confirmed invariants | This remains the current invariant anchor and ships in the main verify path | Implemented | `src/litmus/invariants/mined.py`, `src/litmus/dst/engine.py` |
| Suggested LLM invariants | LLM proposes suggested invariants around changed code | Suggested invariants now ship as heuristic route-gap plus curated store entries, but not as an LLM-backed default path | Partial | `src/litmus/invariants/suggested.py`, `src/litmus/dst/engine.py` |
| Scenario building | Group confirmed and suggested invariants into replayable scenarios | Scenario builder exists; enforcement stays anchored to confirmed invariants only | Implemented | `src/litmus/scenarios/builder.py`, `src/litmus/dst/engine.py` |
| Property checks | Run Hypothesis-style checks over confirmed property invariants | Property runner is wired into verify | Implemented | `src/litmus/properties/runner.py`, `src/litmus/dst/engine.py` |
| Differential replay | Replay mined/captured scenarios against current behavior and classify diffs | Differential replay ships and is used by both verify and replay | Implemented | `src/litmus/replay/differential.py`, `src/litmus/cli.py` |
| Default verification unit | Changed request flows / affected endpoints | Scoped verify exists, but no-argument `verify` still defaults to full repo rather than changed-endpoint-only execution | Partial | `src/litmus/verify_scope.py`, `src/litmus/cli.py` |
| Verify on staged changes | `litmus verify` should run against staged changes | `--staged` is implemented | Implemented | `src/litmus/cli.py`, `src/litmus/discovery/git_scope.py` |
| Verify specific file/dir | `litmus verify src/services/payment.py` | Explicit path-scoped verify is implemented | Implemented | `src/litmus/cli.py`, `src/litmus/verify_scope.py` |
| DST hero path | Patched deterministic runtime + fault injection across I/O boundaries is the hero layer | The shipped verify path now runs multi-seed seeded fault injection and records fault schedules, but the main path is still HTTP-first rather than a fuller multi-layer DST engine | Partial | `src/litmus/dst/engine.py`, `src/litmus/dst/asgi.py`, `src/litmus/simulators/http.py` |
| Exact deterministic replay | Replay exact seed/fault schedule/order of operations | Replay now reuses the stored fault plan, but it is still scenario-level local re-execution rather than a full runtime/order replay contract | Partial | `src/litmus/replay/trace.py`, `src/litmus/mcp/tools.py`, `src/litmus/cli.py` |
| Local seed budget | 100 seeds per scenario by default | Local mode currently uses 3 replay seeds per scenario | Not Implemented | `src/litmus/dst/engine.py` |
| CI seed budget | 500 seeds per scenario in CI mode | CI mode uses 500 replay seeds per scenario | Implemented | `src/litmus/dst/engine.py`, `src/litmus/github_action/report.py` |
| Property max examples | 100 local / 1000 CI | Local is 100, CI is 500 | Partial | `src/litmus/dst/engine.py` |
| Fault profiles | `gentle`, `hostile`, `chaos` profiles configurable via CLI | Internal fault kinds exist, but no user-facing fault-profile config or CLI surface exists | Not Implemented | `src/litmus/dst/faults.py`, `src/litmus/cli.py` |
| Zero-config FastAPI/Starlette path | Supported launch path for Python async ASGI apps | Grounded alpha supports this path and demo/docs validate it | Implemented | `docs/alpha-quickstart.md`, `examples/payment_service/` |
| Zero-config adapters for launch stack | asyncio, `httpx`, `aiohttp`, `sqlalchemy.ext.asyncio`, `redis.asyncio` | HTTP/SQLAlchemy/Redis simulators exist, but shipped verify only patches HTTP and the simulator fidelity is narrower than the full launch story | Partial | `src/litmus/simulators/`, `src/litmus/dst/asgi.py` |
| Honest degradation on unsupported stack | Clearly report what can and cannot be simulated | Core reporting is more honest now, but there is still no richer unsupported-boundary report matching the full spec language | Partial | `src/litmus/reporting/console.py`, `docs/alpha-quickstart.md` |
| GitHub Action | Action runs verify in CI and outputs verdicts | Action exists and is tested | Implemented | `action.yml`, `src/litmus/github_action/report.py` |
| PR comment as dashboard | Publish/update a single Litmus PR comment | Publisher works, paginates, dedupes, and renders suggested review lines | Implemented | `src/litmus/github_action/publish.py`, `src/litmus/reporting/pr_comment.py` |
| Watch mode | Continuous rerun on file save | Implemented, with `.litmus` ignore and stale-artifact cleanup on failures | Implemented | `src/litmus/watch.py` |
| Run/activity records | Stable run-owned verification and replay artifacts | Local/CI/watch/replay now persist file-backed run records with replayable traces | Implemented | `src/litmus/runs/models.py`, `src/litmus/runs/store.py` |
| MCP server | Agent-native verification tool surface | Local stdio MCP server now ships with `verify`, `list_invariants`, `replay`, and `explain_failure` | Implemented | `src/litmus/mcp/server.py`, `tests/integration/test_mcp_server.py` |
| Packaging | `pip install litmus-cli` style packaged CLI | Wheel/sdist build and fresh-venv smoke path are validated in-repo; public publish automation is still absent | Partial | `pyproject.toml`, `tests/e2e/test_packaging_release.py` |
| Homebrew install | `brew install litmus` | No Homebrew distribution path in repo | Not Implemented | `README.md`, repo contents |
| Web dashboard | Post-launch team surface | Not present | Out Of Scope For v0.1 | `product/litmus-product-spec.md` |

## Matrix B: Top-Level README Parity

The top-level `README.md` is intentionally broader than the grounded alpha. This table tracks whether current `main` actually matches those claims.

| README Promise | Current Repo State | Status | Evidence |
| --- | --- | --- | --- |
| `pip install litmus-cli` install story | Package builds and installs locally from a wheel; public publish automation is not in the repo | Partial | `tests/e2e/test_packaging_release.py` |
| `brew install litmus` | No Homebrew distribution path in repo | Not Implemented | `README.md`, repo contents |
| Python 3.10+ | Current packaged/docs path targets Python 3.11+ | Not Implemented | `pyproject.toml`, `docs/alpha-quickstart.md` |
| `litmus verify` “just works” zero-config on supported stack | Grounded alpha works for the demo and supported FastAPI/Starlette path, but broader stack fidelity is still narrower than README language suggests | Partial | `docs/alpha-quickstart.md`, `src/litmus/simulators/` |
| Three layers all under 10 seconds | No enforced product-wide budget; performance is still tracked as a risk | Partial | `product/STATUS.md` |
| Demo shows DST failure `2/100 seeds` and replay of a true faulted bug | Current shipped demo proves the grounded mined-baseline/replay loop; the broader README DST hero script is still ahead of the shipped demo | Partial | `examples/payment_service/`, `tests/e2e/test_demo_payment_flow.py` |
| `litmus init` | Implemented | Implemented | `src/litmus/cli.py`, `src/litmus/init_flow.py` |
| `litmus verify src/services/payment.py` | Path-scoped verify is implemented | Implemented | `src/litmus/cli.py`, `src/litmus/verify_scope.py` |
| `litmus invariants list/edit` | No invariants subcommands in CLI | Not Implemented | `src/litmus/cli.py` |
| `litmus config set dst.seeds ...` | No config subcommands in CLI | Not Implemented | `src/litmus/cli.py` |
| `litmus config set dst.fault-profile hostile` | No config CLI and no user-facing fault-profile selection | Not Implemented | `src/litmus/cli.py`, `src/litmus/dst/faults.py` |
| GitHub Action `uses: rajat1299/litmus@v1` with mode/comment/min-score | Action wrapper exists locally in repo and supports mode/comment/min-score behavior | Implemented | `action.yml`, `src/litmus/github_action/report.py` |
| PR comment contains confidence, failing seeds, explanations | Current renderer/publisher supports this | Implemented | `src/litmus/reporting/pr_comment.py`, `src/litmus/github_action/publish.py` |
| Fault profiles `gentle/hostile/chaos` | Described in README but not surfaced as a real user command | Not Implemented | `README.md`, `src/litmus/cli.py` |
| MCP server support is coming | Repo now ships a local stdio MCP server, so README under-claims current capability | Partial | `src/litmus/mcp/server.py` |

## Bottom Line

### Grounded Alpha

The repo is now strong enough to support a grounded verification-platform alpha story:

- packaged CLI
- runnable demo repo
- `init` / `verify` / `watch` / `replay`
- scoped verify
- seeded HTTP fault injection in the shipped verify path
- replay traces plus replay explanations
- GitHub Action and PR comment publishing
- suggested invariant surfacing with curated-store support
- local stdio MCP access for agents

### Full Product Spec Parity

The repo is **still not at full product-spec parity**.

The biggest missing or partial items are:

1. full DST hero-path depth beyond the current HTTP-first shipped path
2. larger local and CI search budgets matching the broader spec targets
3. richer suggested-invariant approval UX
4. broader CLI/config surfaces described in the README (`invariants`, `config set`, fault profiles)
5. public release/distribution parity with the README (`brew`, published package flow)

### Recommended Framing

Treat Litmus today as:

- **Implemented:** grounded alpha verification platform for Python async ASGI services, including local CLI, CI, PR comments, and agent-native MCP access
- **Not yet implemented:** the complete broader product surface promised by the locked spec and the aspirational top-level README
