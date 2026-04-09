# AI Engineering Confidence Platform Category Definition

## Category

Litmus should define a new category: **AI Engineering Confidence Platform**.

The category is not "AI testing" and not "deterministic simulation" alone. Those are implementation details. The buyer-level promise is:

**Let AI-heavy engineering teams ship machine-written code faster with confidence.**

## Core Problem

AI coding systems increase output faster than existing trust systems can keep up.

What breaks first:

- human review depth collapses under PR volume
- unit and integration tests fail to cover failure-path behavior
- subtle regressions hide inside otherwise reasonable diffs
- teams cannot tell which AI-written changes are routine and which are dangerous
- managers lose confidence in velocity because the cost of a missed failure rises

The new bottleneck is no longer code generation. The new bottleneck is **confidence**.

## Buyer

The broad user base is AI-heavy engineers and engineering teams. The first economic buyer is usually an engineering manager, director, or technical lead responsible for shipping velocity and incident exposure.

The product still needs a developer-led adoption motion:

- the engineer uses Litmus locally or through their coding agent
- the team sees better merge decisions and fewer regressions
- the manager buys the team workflow and policy layer

## Why Now

Three trends create this market:

1. AI-assisted coding is increasing change volume faster than review and QA capacity.
2. The most expensive failures are no longer obvious syntax or type errors; they are system-behavior errors under retries, timeouts, ordering, and partial failure.
3. Existing tools each solve only part of the problem.

Current landscape:

- Claude Code, Cursor, and Copilot help create code.
- Graphite and GitHub help review and route code.
- Antithesis helps deeply test some distributed systems.

No default product owns the end-to-end trust decision for AI-written code.

## Litmus Position

Litmus should sit between code generation and deployment.

Its job is to answer:

- what kind of risk this change introduces
- what verification depth is required
- what evidence supports a ship/no-ship decision
- what the agent or engineer should fix next

That makes Litmus a control layer, not only an engine.

## Initial Wedge

The wedge should be changes where AI generates the most expensive false confidence:

- backend and service-layer changes
- async workflows
- retries, idempotency, rollbacks, queues, webhooks
- changes touching external APIs, caches, and databases

These changes matter because:

- they often look correct in review
- they frequently pass conventional tests
- their failure modes are expensive and delayed

## Category Outcome

If Litmus wins this category, it becomes:

- the trust layer for AI-written changes in local development
- the confidence system of record in CI and pull requests
- the policy engine for which changes can merge and deploy
- the learning layer that turns incidents into future verification rules
