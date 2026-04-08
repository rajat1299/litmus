# Product Status

**Project:** Litmus
**Status Date:** 2026-04-07
**Phase:** Track B2 slice 1 in progress
**Spec Version:** v0.2
**Launch Target Covered By This Repo:** v0.1 product launch

---

## Current Objective

Keep the shipped verification product honest and demonstrable after tranche 1 by closing public-alpha truth drift first, then continue bounded moat-deepening slices without broadening the launch surface or weakening the zero-config contract.

---

## Current Phase

| Area | Status | Notes |
| --- | --- | --- |
| Product direction | Locked | Canonical spec copied into repo |
| Engineering plan | Ready | Master plan written for parallel execution |
| Agent operating model | Ready | Agent handbook and workstream packets added |
| Implementation | Complete | WS-09 through WS-17 are done; tranche 1 is closed, WS-15 cross-layer DST landed, WS-16 replay fidelity landed, and WS-17 target-aware local reachability coverage landed |
| Release readiness | In progress | Demo app, packaged CLI smoke proof, grounded alpha/package docs, tagged release automation, compatibility/degradation reporting, the bounded CLI management surface, the suggested-invariant review lifecycle, and performance/SLO hardening have landed; bounded moat-deepening work now resumes with scheduler-level deterministic replay |

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
| M1 | CLI + config foundation | Complete | `litmus init/verify/watch/replay` command skeleton works |
| M2 | Verification core | Complete | Invariants, property tests, diff tracing, and differential replay run locally |
| M3 | DST engine | Complete | Deterministic runtime and semantic simulators catch seeded failures |
| M4 | Team workflow | Complete | GitHub Action and PR comment are usable end-to-end |
| M5 | Demo-ready launch candidate | In review | Demo app, packaged CLI install path, and launch workflow prove the current alpha loop |
| M6 | Alpha gap closure tranche 1 | Complete | `init`, scoped verify, shipped DST moat work including cross-layer verify, replay/activity records, suggested invariants, and MCP access landed in bounded reviewed slices |

---

## Active Workstreams

Update this table whenever work is claimed, blocked, or completed.

| ID | Workstream | Owner | Status | Dependencies | Last Update |
| --- | --- | --- | --- | --- | --- |
| WS-01 | Repo and CLI foundation | Codex | Done | None | 2026-03-29 |
| WS-02 | App discovery, diff tracing, endpoint mapping | Codex | Done | WS-01 | 2026-03-29 |
| WS-03 | Invariants, scenario sourcing, LLM suggestions | Codex | Done | WS-01, WS-02 | 2026-03-30 |
| WS-04 | Property checks and differential replay | Codex | Done | WS-01, WS-03 | 2026-03-30 |
| WS-05 | Deterministic runtime and DST scheduler | Codex | Done | WS-01, WS-02 | 2026-03-30 |
| WS-06 | Semantic simulators | Codex | Done | WS-05 | 2026-03-30 |
| WS-07 | Reporting, watch mode, GitHub Action | Codex | Done | WS-01, WS-03, WS-04, WS-05, WS-06 | 2026-03-31 |
| WS-08 | Demo app, docs, packaging, release path | Codex | In review | WS-01 through WS-07 | 2026-03-31 |
| WS-09 | Init bootstrap flow | Codex | Done | WS-01, WS-02, WS-03, WS-08 | 2026-04-01 |
| WS-10 | Scoped verify and changed-endpoint selection | Codex | Done | WS-02, WS-04, WS-09 | 2026-04-01 |
| WS-11 | Main-path DST and fault-injection moat work | Codex | Done | WS-05, WS-06, WS-10 | 2026-04-01 |
| WS-12 | Run/activity records and replay artifacts | Codex | Done | WS-04, WS-07, WS-11 | 2026-04-01 |
| WS-13 | Suggested invariants in shipped flow | Codex | Done | WS-03, WS-10, WS-12 | 2026-04-01 |
| WS-14 | MCP surface and minimal shared handlers | Codex | Done | WS-09, WS-10, WS-12, WS-13 | 2026-04-01 |
| WS-15 | Cross-layer DST in shipped verify | Codex | Done | WS-11, WS-12, WS-14 | 2026-04-04 |
| WS-16 | Exact deterministic replay fidelity | Codex | Done | WS-12, WS-15 | 2026-04-04 |
| WS-17 | Fault-path reachability and target-aware local coverage | Codex | Done | WS-15, WS-16 | 2026-04-04 |
| WS-18 | CLI management surface for invariants, config, and fault profiles | Codex | Done | WS-08, WS-13, WS-17 | 2026-04-07 |
| WS-19 | Suggested invariant review workflow | Codex | Done | WS-13, WS-18 | 2026-04-07 |
| WS-20 | Performance and launch SLO hardening | Codex | Done | WS-17, WS-18, WS-19 | 2026-04-07 |
| WS-21 | Scheduler-level deterministic replay slice 1 | Codex | In progress | WS-16, WS-17, WS-20 | 2026-04-07 |

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
| 2026-04-04 | Landed exact replay fidelity via persisted execution transcripts, replay drift classification, and MCP/CLI divergence reporting |
| 2026-04-04 | Chose WS-17 as the next moat slice: bounded fault-path reachability plus deterministic target-aware local coverage |
| 2026-04-04 | Landed WS-17 via fresh-app fault-activation probes, deterministic local target coverage, and persisted target-selection artifacts |
| 2026-04-05 | Completed Track A1 grounded-surface reconciliation across alpha docs, CLI help, MCP descriptions, and reporting labels without changing the aspirational top-level README |
| 2026-04-05 | Completed Track A2 distribution/install automation via single-source version metadata, grounded package metadata, tagged release workflow automation with an explicit manual tag-publish gate, and explicit Homebrew deferral in grounded docs |
| 2026-04-06 | Completed Track A3 compatibility matrix and honest degradation harness via a grounded compatibility doc, shared compatibility payloads in run summaries and MCP verify results, and consistent compatibility reporting in CLI, PR comments, and replay explanations |
| 2026-04-06 | Completed Track A4 implementation on a review branch via bounded `invariants` and `config set` CLI commands, explicit `fault_profile` config, and grounded local verification-depth presets |
| 2026-04-06 | Claimed Track A5 as WS-19 on branch `codex/a5-suggested-invariant-review` with a bounded scope around suggestion review state, provenance, and auditable accept/dismiss/promotion lifecycle |
| 2026-04-07 | Completed Track A5 on `main` via explicit suggestion review state, auditable accept/dismiss flows, and atomic provenance handling that preserves the confirmed-versus-suggested trust boundary |
| 2026-04-07 | Claimed Track A6 as WS-20 on branch `codex/a6-performance-slo-hardening` with a bounded first slice around explicit launch budgets plus timing/budget summaries in run artifacts and verify surfaces |
| 2026-04-07 | Claimed Track B2 slice 1 as WS-21 on branch `codex/b2-scheduler-ledger-slice1` with a bounded hybrid scope: add a scheduler decision ledger plus replay checkpoints, drive replay from the ledger for Litmus-owned decisions, preserve WS-16 fallback behavior for legacy artifacts, and defer full async scheduler capture |

---

## Immediate Next Actions

1. Use `docs/plans/2026-04-05-litmus-next-phase-action-items.md` as the execution map for post-WS-17 launch closeout, moat depth, and platform expansion work.
2. Treat Track A1 as complete and keep the aspirational top-level `README.md` intentionally unchanged.
3. Treat WS-20 as complete on `main` and keep any remaining launch-budget follow-up bounded to explicit review slices.
4. Drive WS-21 through bounded review slices that add scheduler-ledger replay artifacts before any broader runtime rewrites.
5. Keep `product/STATUS.md` as the single live source for what is in flight.

---

## Update Rules

Any agent doing work in this repo must:

1. Read `product/litmus-product-spec.md`.
2. Read `docs/agents/README.md`.
3. Claim a workstream by editing this file before starting substantial work.
4. Update status, blockers, and last update timestamps before handing off.
