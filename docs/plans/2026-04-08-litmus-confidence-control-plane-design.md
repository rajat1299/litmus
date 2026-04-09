# Litmus Confidence Control Plane Design

**Date:** 2026-04-08  
**Status:** future design, not implemented  
**Scope:** first hosted system-of-record contract

---

## Purpose

Define the hosted control plane Litmus should build after the local decision contract is proven.

This document is intentionally design-only. No hosted services, network storage, or remote workers are implemented in this slice.

## Ingest Contract

The control plane should ingest the repo-local verification decision bundle that now persists under `.litmus/runs/`:

- evidence
- risk assessment
- policy evaluation
- verification verdict
- compatibility and degradation details
- replayable artifacts

The hosted system should not recompute those decisions from raw traces unless the contract itself changes.

## First Hosted Objects

- `repository`
- `service`
- `verification_run`
- `evidence_bundle`
- `policy`
- `verdict_history`
- `incident`

## First Hosted Workflows

- PR ingest and run association
- verdict persistence
- merge-gate evaluation from persisted policy outcomes
- service-level policy assignment
- incident ingestion and linkage to prior verdicts

## Design Constraint

Do not harden hosted abstractions ahead of the local contract.

The control plane deserves implementation only after the local decision bundle is stable enough that:

- CLI, PR, and MCP surfaces all tell the same decision story
- unsupported gaps and policy failures are explicit
- the review team agrees the local object boundaries are worth preserving
