# WS-16 Exact Deterministic Replay Fidelity Design

## Goal

Deepen the Litmus moat from "re-run the same request with the same fault plan" into "re-run the recorded failure and tell the user whether execution actually matched the recorded failure contract."

## Why This Slice Is Next

WS-15 made the shipped `litmus verify` path meaningfully stronger by adding narrow, zero-config cross-layer DST across HTTP, SQLAlchemy async, and Redis async on a supported surface. That raised the value of failing seeds, but it also raised the cost of weak replay semantics.

Today, `litmus replay <seed>` is still mostly:

- reload the stored request
- rebuild the stored `FaultPlan`
- execute the request again
- classify the response diff

That is useful, but it is not yet the deterministic replay contract promised in the product spec. A replay can currently produce the same response for the wrong reason, or a different response without explaining where execution drifted first. Once Litmus is finding higher-value cross-layer failures, that trust gap becomes the biggest moat gap left in the local developer loop.

## Product Decision

This slice will make replay an execution-fidelity product feature.

Litmus will:

- persist a normalized execution transcript for each recorded replay seed
- re-derive the same transcript on `litmus replay <seed>`
- compare the recorded transcript to the replay transcript
- report whether execution matched or drifted
- surface the first meaningful divergence in CLI, MCP, and run artifacts

Litmus will not, in this slice:

- implement a full deterministic scheduler or async interleaving recorder
- change the current supported boundary surface
- increase seed counts
- broaden simulator fidelity outside the existing shipped verify path

## Approaches Considered

### Option 1: Keep response-diff replay and improve messaging

This is the smallest change: keep current replay semantics and only explain the rerun more clearly.

Why reject it:

- it does not close the trust gap
- it still cannot distinguish "same output, different execution" from "same output, same execution"
- it leaves the product spec claim effectively unmet

### Option 2: Persist and compare a normalized execution transcript

This is the recommended option.

The core idea is:

- keep using the existing verify and replay execution path
- derive a stable, ordered execution transcript from `TraceEvent`s
- compare recorded and replay transcripts at replay time
- classify fidelity as `matched`, `drifted`, or `not_checked`

Why this is right now:

- it materially improves the moat without a runtime rewrite
- it uses artifacts Litmus already records
- it gives the developer the missing answer: where replay stopped matching

### Option 3: Build a full execution-order deterministic runtime

This would try to make the runtime itself the full replay engine.

Why defer it:

- it is too invasive for the next bounded slice
- it mixes runtime research with product trust repair
- it would delay value while increasing implementation and review risk

## Recommended Architecture

### 1. Replay Trace Records Become Execution Artifacts

`ReplayTraceRecord` in [trace.py](/Users/rajattiwari/litmus/src/litmus/replay/trace.py) should keep the raw `TraceEvent` list, but it should also persist a normalized execution transcript derived from that trace.

That transcript should be:

- ordered
- stable across runs
- stripped of incidental metadata
- specific enough to detect meaningful drift

The comparison surface should be built from checkpoints such as:

- fault plan selection
- boundary interception and simulation
- fault injection
- defaulted responses
- application exception
- final response emission

The key rule is that fidelity compares execution semantics, not raw trace payloads.

### 2. Introduce A Replay Fidelity Model

Add an explicit replay fidelity contract instead of overloading `ReplayExplanation.reasons`.

The model should answer:

- was fidelity checked?
- did replay execution match the recorded execution?
- if not, what was the first divergence?

The minimal contract should include:

- `status`
  - `matched`
  - `drifted`
  - `not_checked`
- `recorded_step`
- `replay_step`
- `reason`
- `recorded_checkpoint`
- `replay_checkpoint`

`not_checked` is required for honest degradation on older run artifacts that predate WS-16.

### 3. Replay Comparison Runs On The Existing Replay Path

`_execute_replay()` in [tools.py](/Users/rajattiwari/litmus/src/litmus/mcp/tools.py) should keep the current replay flow:

- load stored replay record
- execute `run_asgi_app()` with the reconstructed fault plan
- classify the response diff

Then, after execution, it should:

- build the replay transcript from the new trace
- compare it to the stored transcript
- attach the fidelity result to the returned explanation

This keeps WS-16 bounded. The replay command becomes more truthful without needing a different runner.

### 4. Explanation And Output Contract

Replay output should stop implying that response diff alone is the replay answer.

CLI and MCP should surface both:

- response classification
- execution fidelity

Examples:

- `Execution fidelity: matched`
- `Execution fidelity: drifted at step 4`
- `Recorded: fault_injected(redis, timeout)`
- `Replay: boundary_detected(redis)`

This is the user-facing trust repair. A developer should immediately know whether Litmus reproduced the same failure mechanics or merely reran the same seed.

### 5. Backward Compatibility

Existing `.litmus/runs/` artifacts will not all have a stored transcript.

WS-16 should not invalidate them. Instead:

- replay should continue to run against older records
- fidelity should report `not_checked`
- explanation text should say that the artifact predates fidelity recording

That keeps the command stable while making the product honest about replay depth.

## Data Flow

1. `litmus verify` runs the existing replay/differential loop.
2. For each stored replay seed, Litmus derives a normalized execution transcript from the recorded trace and persists it with the replay record.
3. `litmus replay <seed>` reloads the stored replay record.
4. Litmus reconstructs the stored `FaultPlan` and reruns the request.
5. Litmus derives a new normalized transcript from the replay trace.
6. Litmus compares recorded vs replay transcript and produces a fidelity result.
7. CLI, MCP, run summaries, and PR-facing explanation surfaces render both classification and fidelity.

## Testing Strategy

### Unit

- transcript normalization from raw `TraceEvent`s
- transcript comparison behavior
- first-divergence selection
- backward-compatible `not_checked` handling for old replay records

### Integration

- `litmus replay <seed>` reports `matched` when replay follows the same recorded path
- `litmus replay <seed>` reports `drifted` when execution no longer reaches the same boundary/fault sequence
- MCP replay and explain operations return the same fidelity result as the CLI

### Regression Shape

At least one fixture should prove a replay drift that is not captured by status/body diff alone. The product value is strongest when the test demonstrates:

- same request
- same seed
- same stored fault plan
- different execution transcript

## Non-Goals

- scheduler-level deterministic interleaving
- coverage expansion beyond the WS-15 supported boundary surface
- seed-budget increases
- new fault-profile UX
- cloud or remote replay

## Risks And Guards

### Risk: overfitting fidelity to unstable trace noise

Guard: normalize `TraceEvent`s into a small checkpoint vocabulary and compare that, not arbitrary raw metadata.

### Risk: breaking old replay artifacts

Guard: add explicit `not_checked` fidelity semantics for pre-WS-16 runs.

### Risk: creating a second replay truth model

Guard: keep the raw trace as the source artifact and derive the normalized transcript from it, rather than inventing an unrelated replay log.

### Risk: making replay explanations too verbose

Guard: surface only the first meaningful divergence in the primary output and keep deeper detail in structured data.

## Success Criteria

WS-16 is done when:

- `litmus replay <seed>` can say whether execution matched the recorded failure path
- replay explanations surface the first meaningful divergence when fidelity drifts
- old artifacts degrade honestly as `not_checked`
- MCP returns structured fidelity data instead of only response-diff explanation
- the implementation does not change seed counts, supported boundaries, or runtime scheduling semantics
