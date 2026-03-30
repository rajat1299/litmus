# Product Status

**Project:** Litmus
**Status Date:** 2026-03-29
**Phase:** Pre-development / execution setup
**Spec Version:** v0.2
**Launch Target Covered By This Repo:** v0.1 product launch

---

## Current Objective

Stand up the repo, execution model, and workstream structure required to build the Python-first v0.1 product in parallel with multiple coding agents and continuous review.

---

## Current Phase

| Area | Status | Notes |
| --- | --- | --- |
| Product direction | Locked | Canonical spec copied into repo |
| Engineering plan | Ready | Master plan written for parallel execution |
| Agent operating model | Ready | Agent handbook and workstream packets added |
| Implementation | Not started | No product code in repo yet |
| Release readiness | Not started | Depends on implementation and demo app |

---

## Locked Decisions

- Launch product is DST-first and Python-first.
- The supported launch path is zero-config on FastAPI/Starlette async stacks.
- The default verification unit is affected request flows/endpoints.
- Mined tests are the invariant anchor; LLM invariants are suggested extensions.
- Semantic simulators are the launch external-state model.
- `litmus watch` is the acquisition hook; GitHub Action + PR comment is the conversion path.

---

## Milestones

| ID | Milestone | Status | Exit Condition |
| --- | --- | --- | --- |
| M0 | Repo operating system | Complete | Spec, plan, status, and workstream docs exist |
| M1 | CLI + config foundation | Queued | `litmus init/verify/watch/replay` command skeleton works |
| M2 | Verification core | Queued | Invariants, property tests, diff tracing, and differential replay run locally |
| M3 | DST engine | Queued | Deterministic runtime and semantic simulators catch seeded failures |
| M4 | Team workflow | Queued | GitHub Action and PR comment are usable end-to-end |
| M5 | Demo-ready launch candidate | Queued | Demo app and launch workflow prove the hero loop |

---

## Active Workstreams

Update this table whenever work is claimed, blocked, or completed.

| ID | Workstream | Owner | Status | Dependencies | Last Update |
| --- | --- | --- | --- | --- | --- |
| WS-01 | Repo and CLI foundation | Codex | In review | None | 2026-03-29 |
| WS-02 | App discovery, diff tracing, endpoint mapping | Unassigned | Queued | WS-01 | 2026-03-29 |
| WS-03 | Invariants, scenario sourcing, LLM suggestions | Unassigned | Queued | WS-01, WS-02 | 2026-03-29 |
| WS-04 | Property checks and differential replay | Unassigned | Queued | WS-01, WS-03 | 2026-03-29 |
| WS-05 | Deterministic runtime and DST scheduler | Unassigned | Queued | WS-01, WS-02 | 2026-03-29 |
| WS-06 | Semantic simulators | Unassigned | Queued | WS-05 | 2026-03-29 |
| WS-07 | Reporting, watch mode, GitHub Action | Unassigned | Queued | WS-01, WS-03, WS-04, WS-05, WS-06 | 2026-03-29 |
| WS-08 | Demo app, docs, packaging, release path | Unassigned | Queued | WS-01 through WS-07 | 2026-03-29 |

---

## Risks And Blockers

| ID | Risk / Blocker | Severity | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Monkey-patching may fail across library versions | High | Unassigned | Pin supported versions and test a narrow compatibility matrix |
| R2 | Semantic simulators may be too shallow for common app patterns | High | Unassigned | Keep simulator scope explicit and add golden scenarios early |
| R3 | Local verify may exceed 10 seconds | High | Unassigned | Track performance budgets from the first implementation step |
| R4 | LLM invariant suggestions may create trust noise | Medium | Unassigned | Keep mined invariants clearly separated from suggested invariants |
| R5 | App discovery may fail on non-standard layouts | Medium | Unassigned | Support explicit app configuration from day one |

---

## Decision Log

| Date | Decision |
| --- | --- |
| 2026-03-29 | Chose option 2 repo structure: canonical spec, master plan, status file, agent handbook, workstream packets |
| 2026-03-29 | Chose parallel multi-agent execution with continuous review and evaluation |
| 2026-03-29 | Canonicalized spec from `litmus-product-spec-v0.2.md` into repo with minor hardening edits |

---

## Immediate Next Actions

1. Initialize the actual Python project and packaging/tooling skeleton.
2. Claim WS-01 and WS-02 so route discovery and CLI scaffolding can start in parallel.
3. Keep `product/STATUS.md` as the single live source for what is in flight.

---

## Update Rules

Any agent doing work in this repo must:

1. Read `product/litmus-product-spec.md`.
2. Read `docs/agents/README.md`.
3. Claim a workstream by editing this file before starting substantial work.
4. Update status, blockers, and last update timestamps before handing off.
