# B2 Scheduler-Level Deterministic Replay Design

**Status Date:** 2026-04-07
**Workstream:** WS-21
**Branch:** `codex/b2-scheduler-ledger-slice1`
**Scope:** First bounded Track B slice for scheduler-level deterministic replay

---

## Goal

Move Litmus replay beyond response-oriented transcript comparison by introducing a replay-driving scheduler decision ledger for the deterministic choices Litmus actually owns today, while keeping execution checkpoints as the validation and explanation surface.

## Why This Slice Exists

WS-16 made `litmus replay` honest by persisting execution transcripts and comparing replay output to those recorded artifacts. That work does not yet create a real scheduler contract because the persisted artifact is still derived from coarse trace events rather than the runtime's own ordered decision model.

The first B2 slice should cross that boundary without overreaching. It should let Litmus say:

"Litmus replay did not just rerun the same seed. It followed the same recorded scheduler-owned decisions until this exact divergence point."

## Non-Goals

This slice does not attempt:

- full Python event-loop interleaving replay
- full coroutine scheduling capture
- arbitrary async causal reconstruction
- a general-purpose time-travel runtime

Those belong to later moat work, not this first artifact/model slice.

## Contract

The bounded hybrid contract for B2 slice 1 is:

- **Scheduler decision ledger is the replay-driving source of truth.**
- **Execution checkpoints are the replay-validation and explanation anchors.**

This means replay must consume the recorded ordered ledger for Litmus-owned decisions, not reconstruct those decisions only from the seed plus a fault-plan transcript. Checkpoints remain the user-facing alignment story that explains where replay stayed on contract or drifted.

## Scheduler-Owned Decisions In Scope

Slice 1 records only decisions Litmus already owns inside the current runtime and replay planning flow:

- replay seed identity
- scenario identity
- selected fault target
- selected fault kind
- planned probe or seed target sequence
- scheduler-controlled boundary fault activation decisions
- deterministic Litmus-native branch choices made while applying replay/fault scheduling

If a decision is not currently controlled by Litmus, it is out of scope for this slice.

## Checkpoint Anchors In Scope

Slice 1 also records a small checkpoint stream that stays understandable and useful for explanation:

- request start
- boundary enter
- boundary exit
- fault injected
- fault defaulted
- fault bypassed
- app exception
- response start
- response complete

These are not replay-driving decisions. They are alignment anchors.

## Replay Semantics

On replay, Litmus should:

1. Load the recorded scheduler ledger.
2. Require Litmus-controlled decisions to occur in the same order.
3. Emit a fresh checkpoint stream during replay.
4. Compare decision order first, then checkpoint alignment, then outcome alignment.
5. Report the first meaningful divergence with a specific drift taxonomy.

## Drift Taxonomy

The first bounded taxonomy is:

- `decision_mismatch`
- `decision_missing`
- `unexpected_decision`
- `checkpoint_drift`
- `outcome_drift`

Legacy WS-16 artifacts that do not have a scheduler ledger must continue to degrade honestly rather than pretending to satisfy the new contract.

## Artifact Shape

`ReplayTraceRecord` gains two new Litmus-native artifact surfaces:

- `scheduler_ledger`
- `replay_checkpoints`

The existing `execution_transcript` remains as a legacy compatibility field for older artifacts and for a bounded fallback path during rollout.

## Implementation Boundary

Claude Code patterns are relevant only for:

- ordered artifact normalization
- schema/version discipline
- run/artifact lifecycle consistency

They are not a source of runtime logic. The scheduler model, ledger semantics, checkpoint taxonomy, replay contract, and drift reasoning remain Litmus-native.

## Slice-1 Exit Criteria

This first B2 slice is complete when:

- replay artifacts persist an ordered scheduler decision ledger
- replay consumes that ledger instead of deriving the driving decisions only from trace transcripts
- drift can be reported as scheduler/order mismatch rather than only transcript mismatch
- older WS-16 artifacts still fall back honestly
