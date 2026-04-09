# 0 To 1 Wedge

## Goal

Turn Litmus from an impressive verification alpha into a paid product that AI-heavy engineering teams adopt because it catches expensive backend failures before merge.

## First Customer

The first real customer is an AI-heavy product engineering team shipping backend services quickly with limited review bandwidth.

Typical shape:

- 5 to 50 engineers
- heavy Claude Code / Cursor / Copilot usage
- Python, TypeScript, or mixed backend stack
- significant API and service-layer logic
- real production exposure to payments, auth, integrations, or data workflows

## First Use Case

The first use case is not broad code quality.

It is:

**"This AI-written backend change passed tests. Should we trust it enough to merge?"**

Best-fit examples:

- retry and idempotency logic
- webhook handlers
- external API integration changes
- transactional service changes
- cache, queue, and DB coordination changes

## Initial Product Flow

1. Agent or developer writes a change.
2. Litmus classifies the diff and identifies risky codepaths.
3. Litmus runs the right verification recipe.
4. Litmus emits a confidence verdict plus evidence.
5. The agent or engineer fixes the issue or the PR merges with clear support.

## Minimum Paid Product

The first paid product should include:

- local developer verification
- PR checks with confidence verdicts
- merge gating by policy
- evidence bundles and replayable failures
- service- or repo-level policy settings

It does not yet need:

- a broad executive dashboard
- enterprise observability integrations
- a large platform team workflow
- universal stack coverage

## Wedge Narrative

The first narrative should be:

**"Litmus catches the backend failures AI codegen creates and human review misses."**

That is better than a generic trust or governance pitch because:

- it is concrete
- it is expensive
- it has measurable ROI
- it creates urgency for the buyer

## Success Metrics

The 0-to-1 wedge should be managed against a small set of hard metrics:

- percent of AI-written PRs verified
- percent of risky PRs with action-changing findings
- time from failed verification to rerun-to-green
- reduction in merge-time uncertainty for backend changes
- number of incidents or rollback classes converted into reusable checks

## 0 To 1 Product Priorities

1. Make the verdict operationally trustworthy.
2. Make agent and PR workflows extremely fast.
3. Make unsupported coverage visible and explicit.
4. Build incident-to-regression learning early.
5. Prove ROI on a narrow set of expensive failure classes.

## Things To Avoid Early

- broadening into generic static analysis
- building a large dashboard before the verdict is trusted
- chasing every language before the wedge is repeatable
- becoming a consultancy around simulator customization
- turning the product into a long-running infra project with weak user feedback loops
