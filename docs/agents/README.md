# Agent Operating Guide

This repository is designed for parallel coding-agent execution with continuous review and evaluation.

Read these files in order before doing substantial work:

1. `product/litmus-product-spec.md`
2. `product/STATUS.md`
3. `docs/plans/2026-03-29-litmus-engineering-plan.md`
4. your assigned file in `docs/agents/workstreams/`

---

## Core Rules

1. Claim work in `product/STATUS.md` before editing implementation files.
2. Work inside a bounded workstream. Do not widen scope silently.
3. Prefer disjoint file ownership. If a shared interface must change, document it first.
4. Update status before handing off or stopping.
5. Every workstream must end with targeted verification and a review note.

---

## Claiming Work

When taking a workstream:

1. Set yourself as owner in `product/STATUS.md`.
2. Change the workstream status to `In progress`.
3. Add the date to `Last Update`.
4. Read the dependencies and interface notes in the workstream file.

If the repo is under git, use a worktree or branch that matches the workstream, for example:

- `codex/ws-01-cli-foundation`
- `codex/ws-05-dst-runtime`

---

## Continuous Review Loop

Every work cycle should follow this pattern:

1. Read the workstream packet and confirm scope.
2. Implement the smallest coherent slice.
3. Run the narrowest reliable tests first.
4. Summarize changed files and outcomes.
5. Request or perform independent review before marking done.

Do not defer review until the end of the product.

---

## Handoff Format

Use this exact structure when handing off work:

```md
## Handoff

**Workstream:** WS-XX
**Status:** done | blocked | partial
**Files Changed:** ...
**Tests Run:** ...
**Results:** ...
**Open Risks:** ...
**Next Recommended Step:** ...
```

---

## Definition Of Done

A workstream or slice is only done when:

- the scoped deliverable exists
- targeted tests pass
- relevant docs are updated
- `product/STATUS.md` reflects reality
- handoff notes are written
- review has happened or is explicitly queued

If the code changed but the status file and docs did not, the work is not done.
