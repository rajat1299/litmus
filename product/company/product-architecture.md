# Product Architecture

## Product Thesis

Litmus should be built as a **confidence system**, not a single verification engine.

The core architecture is:

`diff -> risk classification -> verification plan -> evidence bundle -> confidence verdict -> merge/deploy action`

## Layer 1: Change Intelligence

This layer turns a code change into a structured risk object.

It should answer:

- what changed
- which services and boundaries are affected
- likely blast radius
- which risk classes apply
- what verification depth is required

Core risk classes:

- reliability risk
- broad correctness risk
- migration and data integrity risk
- external dependency risk
- agent-generated novelty risk

This layer is what prevents Litmus from behaving like a one-size-fits-all test runner.

## Layer 2: Verification Engine

This is the current seed of the product in this repo.

Over time, the engine should route across multiple verification modes:

- deterministic replay
- seeded fault injection
- property checks
- baseline regression
- incident-derived regression checks
- policy verification
- targeted generated tests where useful

The engine should not treat every diff equally. It should choose the right verifier for the risk object produced by the change-intelligence layer.

## Layer 3: Confidence Control Plane

This is the team product and the system of record.

It stores:

- verdicts
- confidence scores
- unsupported gaps
- evidence bundles
- policy outcomes
- historical failure patterns
- service criticality
- team and repo trust trends

This is the layer that powers:

- PR merge gates
- review routing
- auditability
- manager dashboards
- deploy controls
- API integrations for internal agents

## Product Surfaces

### Developer Surface

Litmus should integrate into the agent and editor loop.

Core outcome:

- "verify this change"
- get a verdict
- get failure evidence
- get the next fix to make

### PR Surface

Every PR should get:

- risk classification
- confidence verdict
- verification evidence
- missing coverage callouts
- merge recommendation

### Team Surface

Leads and platform owners should get:

- policy controls by repo or service
- confidence thresholds
- critical-path service settings
- trends across AI-written changes
- top repeated failure modes

### Platform API

Litmus should expose its decision model as an API so internal agents, CI systems, and deployment systems can call it directly.

## Decision Model

The system output cannot just be a number.

Litmus should return a structured decision:

- safe to merge
- safe with caveats
- needs deeper verification
- unsafe to merge
- unsupported / insufficient evidence

That output is usable by both humans and agents.

## Design Rule

The engine is necessary but insufficient.

A venture-scale Litmus product wins only if it owns:

- the risk model
- the verification plan
- the confidence verdict
- the policy consequence

Not just the test execution.
