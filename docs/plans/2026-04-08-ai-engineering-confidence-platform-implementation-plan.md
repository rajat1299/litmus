# AI Engineering Confidence Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the approved venture-scale Litmus company thesis into a staged product execution roadmap that expands the current verification alpha into an AI engineering confidence platform.

**Architecture:** Keep the current verification engine as the technical wedge, then add a change-intelligence layer above it and a confidence control plane around it. Sequence work so the product first wins on high-risk backend verification, then broadens into PR confidence, policy, and incident-driven learning.

**Tech Stack:** Python CLI and MCP surfaces, GitHub Action, local run artifacts under `.litmus/`, future hosted control-plane services, PR integrations, and service-level policy storage.

---

### Task 1: Lock the company narrative and source-of-truth documents

**Files:**
- Create: `product/company/README.md`
- Create: `product/company/category-definition.md`
- Create: `product/company/product-architecture.md`
- Create: `product/company/0-to-1-wedge.md`
- Create: `product/company/1-to-10-expansion.md`
- Create: `product/company/moat-map.md`
- Create: `product/company/gtm-and-pricing.md`
- Create: `docs/plans/2026-04-08-ai-engineering-confidence-platform-design.md`

**Step 1: Review the approved design language**

Read:
- `product/litmus-product-spec.md`
- `docs/alpha-quickstart.md`
- `product/company/*.md`

Expected: the venture thesis stays clearly separated from the grounded alpha surface.

**Step 2: Verify cross-document consistency**

Check that every company doc uses the same core thesis:

- Litmus is the confidence layer for AI-native engineering teams
- the wedge is high-risk backend and distributed failures
- the long-term product is broader than the current repo surface

Expected: no contradictions between category, architecture, wedge, moat, and GTM docs.

**Step 3: Commit**

```bash
git add product/company docs/plans/2026-04-08-ai-engineering-confidence-platform-design.md
git commit -m "docs: add Litmus company blueprint"
```

### Task 2: Define the 0-to-1 product requirements from the company thesis

**Files:**
- Modify: `product/company/0-to-1-wedge.md`
- Create: `docs/plans/2026-04-08-litmus-0-to-1-product-requirements.md`
- Modify: `product/STATUS.md`

**Step 1: Write the first concrete product requirement doc**

Create a doc that translates the wedge into requirements:

- first ICP
- core workflows
- must-have evidence types
- must-have policies
- unsupported gaps that must stay explicit

**Step 2: Add a new status-track entry**

Update `product/STATUS.md` with a new post-WS-23 track for:

- change intelligence
- hosted control plane
- policy and merge controls
- incident learning

Expected: strategy work is visible in the repo's live status model.

**Step 3: Commit**

```bash
git add product/company/0-to-1-wedge.md docs/plans/2026-04-08-litmus-0-to-1-product-requirements.md product/STATUS.md
git commit -m "docs: define Litmus 0-to-1 product requirements"
```

### Task 3: Design the change-intelligence layer

**Files:**
- Create: `docs/plans/2026-04-08-litmus-change-intelligence-design.md`
- Modify: `product/company/product-architecture.md`

**Step 1: Specify the risk-object model**

Document:

- risk classes
- blast-radius factors
- service criticality
- unsupported-coverage penalties
- evidence requirements per risk class

**Step 2: Define how it plugs into current verification**

Map current repo capabilities to the future model:

- replay
- fault injection
- property checks
- scoped verify
- MCP verify

Expected: a clear bridge from today's engine to tomorrow's planner.

**Step 3: Commit**

```bash
git add docs/plans/2026-04-08-litmus-change-intelligence-design.md product/company/product-architecture.md
git commit -m "docs: design Litmus change intelligence layer"
```

### Task 4: Design the hosted confidence control plane

**Files:**
- Create: `docs/plans/2026-04-08-litmus-confidence-control-plane-design.md`
- Modify: `product/company/product-architecture.md`
- Modify: `product/company/1-to-10-expansion.md`

**Step 1: Define core hosted objects**

Document:

- repositories
- services
- PR verdicts
- evidence bundles
- policies
- incidents
- confidence history

**Step 2: Define first hosted workflows**

Document:

- PR ingest
- verdict persistence
- merge gating
- service-level policy enforcement
- historical trend views

**Step 3: Commit**

```bash
git add docs/plans/2026-04-08-litmus-confidence-control-plane-design.md product/company/product-architecture.md product/company/1-to-10-expansion.md
git commit -m "docs: design Litmus confidence control plane"
```

### Task 5: Design the incident-learning loop

**Files:**
- Create: `docs/plans/2026-04-08-litmus-incident-learning-design.md`
- Modify: `product/company/moat-map.md`
- Modify: `product/company/1-to-10-expansion.md`

**Step 1: Define incident ingestion and normalization**

Document how Litmus should capture:

- incidents
- rollbacks
- postmortem findings
- repeated verification failures

**Step 2: Define output artifacts**

Document how incidents become:

- invariants
- verification recipes
- service-level policies
- updated risk scores

**Step 3: Commit**

```bash
git add docs/plans/2026-04-08-litmus-incident-learning-design.md product/company/moat-map.md product/company/1-to-10-expansion.md
git commit -m "docs: design Litmus incident learning loop"
```

### Task 6: Translate strategy into product roadmap and pricing assumptions

**Files:**
- Modify: `product/company/gtm-and-pricing.md`
- Create: `docs/plans/2026-04-08-litmus-company-roadmap.md`

**Step 1: Build a staged roadmap**

Split roadmap into:

- next 6 months
- next 12 months
- next 24 months

Each stage should name:

- product goal
- main technical dependency
- GTM milestone
- pricing implication

**Step 2: Pressure-test packaging**

Define the transition from:

- free developer utility
- paid team workflow
- enterprise control plane

Expected: pricing aligns with workflow ownership and buyer value, not just compute.

**Step 3: Commit**

```bash
git add product/company/gtm-and-pricing.md docs/plans/2026-04-08-litmus-company-roadmap.md
git commit -m "docs: add Litmus company roadmap"
```
