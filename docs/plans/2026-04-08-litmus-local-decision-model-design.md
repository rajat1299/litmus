# Litmus Local Decision Model Design

**Date:** 2026-04-08  
**Status:** approved design  
**Scope:** first repo-local confidence-platform slice

---

## Goal

Turn Litmus from a flat confidence-score reporter into a local decision system that can explain:

- what risk this change appears to carry
- what evidence Litmus gathered
- what policy checks passed or failed
- what verdict Litmus recommends right now

This slice stays fully local. The system of record remains file-backed under `.litmus/runs/`.

## Design Rule

The next gap is semantic, not infrastructural.

Litmus should not introduce hosted service boundaries until the local product contract is sharp enough to deserve a control plane. This slice therefore adds first-class local domain objects for:

- `risk_assessment`
- `evidence`
- `policy_evaluation`
- `verification_verdict`

## Local Decision Contract

### Risk Assessment

Litmus derives a bounded repo-local risk object from what it already knows today:

- affected scope: app reference, scope label, routes, scenarios
- risk classes inferred from exercised boundaries and checks
- unsupported gaps found during detection/interception
- evidence expectations required for this run shape

The first shipped risk classes are:

- `reliability`
- `correctness`
- `external_dependency`
- `data_integrity`

The first shipped risk levels are:

- `low`
- `elevated`
- `high`

These levels are intentionally heuristic and local. They are not yet service-criticality or incident-informed scores.

### Evidence

Litmus groups the existing run evidence into a stable object rather than forcing downstream surfaces to infer it from unrelated counts:

- replay counts
- property-check counts
- invariant counts
- pending review count
- detected boundary count
- unsupported gap count
- total decision signals
- confidence score

This keeps the current alpha evidence honest while making it consumable by a future control plane.

### Policy Evaluation

Litmus applies a narrow local decision policy named `alpha_local_v1` by default.

The first checks are:

- `blocking_regressions`
- `sufficient_evidence`
- `supported_boundary_coverage`
- `suggested_invariant_review` as a warning-only check

The first merge recommendations are:

- `allow`
- `review_required`
- `block`

Repo-local config can tighten that merge behavior with `strict_local_v1`, which keeps the same four semantic decision values but upgrades `sufficient_evidence` and `supported_boundary_coverage` failures from `review_required` to `block`.

Entry points may also override the repo default per run. That override is still local and advisory-state only: it changes the policy outcome for the current CLI, MCP, or GitHub Action execution without introducing hosted policy storage.

This policy is advisory in the local CLI surface and explicit in PR/MCP surfaces. It is the precursor to future hosted merge/deploy policy.

### Verification Verdict

Litmus returns a structured verdict instead of only a score:

- `safe`
- `unsafe`
- `needs_deeper_verification`
- `insufficient_evidence`

Initial decision mapping:

- any breaking replay or failed property check -> `unsafe`
- no replay/property signals -> `insufficient_evidence`
- detected unsupported gaps without blocking regressions -> `needs_deeper_verification`
- otherwise -> `safe`

## Product Surface Changes

### CLI

`litmus verify` should continue to show the grounded alpha summary, but now lead with:

- verdict
- merge recommendation
- risk level and risk classes
- failed or warning policy checks

Local CLI exit behavior stays grounded to current alpha expectations for this slice. The decision model becomes visible before local enforcement broadens.

### PR Surface

PR comments should stop reading like score-only reports and instead render:

- decision
- merge recommendation
- risk summary
- policy failures or warnings
- explicit unsupported gaps
- the underlying evidence counts

### MCP Surface

`verify` should expose typed payloads for:

- `risk_assessment`
- `evidence`
- `policy_evaluation`
- `verification_verdict`

Existing counts remain for backward compatibility.

## Persistence Boundary

The durable local storage boundary is the verification projection persisted into `.litmus/runs/<run_id>/run.json`.

This slice adds the new decision objects to that persisted summary so a future hosted plane can ingest one coherent payload rather than reconstruct decisions from raw counts.

## Future Hosted Control Plane

The hosted control plane remains future work. When it exists, it should treat the local decision bundle as the first ingest contract.

The first hosted objects should be:

- repository
- service
- pull request verification run
- evidence bundle
- policy
- verdict history
- incident

The first hosted workflows should be:

- PR ingest
- verdict persistence
- merge-gate evaluation
- service-level policy assignment
- incident-to-policy feedback

None of that is implemented in this slice.
