# 1 To 10 Expansion

## Expansion Principle

Litmus should expand by moving up the decision stack, not by only adding more simulator depth.

The sequence should be:

1. own verification for high-risk backend changes
2. own confidence decisions across the PR lifecycle
3. own policy and learning for AI-native software delivery

## Stage 1: Reliability Verifier

This is the wedge.

Litmus is primarily known for:

- deterministic replay
- failure-path verification
- catching async and distributed reliability bugs
- replayable evidence for agent-written regressions

This gets developer love and early proof of value.

## Stage 2: PR Confidence Layer

Once the engine is trusted, Litmus should expand to broader change-risk evaluation.

New capabilities:

- typed diff risk classification
- confidence-aware PR checks
- review routing by risk instead of ownership alone
- merge gating based on service criticality and evidence quality
- unsupported-gap reporting as a first-class merge signal

At this stage, Litmus starts to overlap with Graphite-like workflow products, but with a deeper technical decision engine underneath.

## Stage 3: Organizational Learning Layer

The next expansion is a durable learning loop.

Litmus should turn:

- incidents
- rollbacks
- postmortems
- repeated PR failures
- manually approved or rejected risk decisions

into:

- reusable invariants
- verification recipes
- service-specific policies
- stronger diff-risk prediction

This is where the product gets better as the customer uses it more.

## Stage 4: Deploy And Runtime Controls

The eventual product should influence more than merges.

Expansion surfaces:

- deploy readiness verdicts
- canary and rollout gating
- runtime-informed verification requirements
- policy for which AI agents can autonomously merge or deploy

This is the path from trust in code to trust in software delivery.

## Stage 5: Multi-Stack Confidence Platform

Only after the workflow and learning system are working should Litmus broaden stack coverage aggressively.

Expansion order should follow customer pain:

- TypeScript and Node service stacks
- database migration workflows
- queue and event-driven systems
- security-sensitive service paths
- frontend-backend contract changes

The rule is simple: expand where it improves the confidence verdict for AI-heavy teams, not where it is merely technically interesting.

## End State

The mature company position is:

**Litmus is the system that decides how much trust an AI-written change has earned.**

That end state supports:

- local engineering workflows
- team policy
- autonomous agent integration
- deploy controls
- org-wide trust analytics
