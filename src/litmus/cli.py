from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from litmus.discovery.app import load_asgi_app
from litmus.dst.asgi import run_asgi_app
from litmus.dst.engine import run_verification
from litmus.init_flow import bootstrap_repo
from litmus.invariants.models import RequestExample, ResponseExample
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification, run_differential_replay
from litmus.replay.trace import replay_record_for_seed, save_replay_trace_records
from litmus.reporting.console import render_replay_summary, render_verification_summary
from litmus.scenarios.builder import Scenario
from litmus.verify_scope import resolve_verification_scope
from litmus.watch import run_watch

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Deterministic fault-injection verification for agent-written code.",
)


@app.command()
def init() -> None:
    """Bootstrap Litmus in the current repository."""
    try:
        result = bootstrap_repo(Path.cwd())
    except LookupError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None

    typer.echo("Litmus init")
    typer.echo(f"App: {result.app_reference}")
    typer.echo(f"Config: {result.config_status} {result.config_path.name}")
    typer.echo(
        "Invariants: "
        f"{result.invariants_status} .litmus/invariants.yaml ({result.invariant_count} mined)"
    )
    typer.echo(f"Support: {result.support_summary[0]}")


@app.command()
def verify(
    target: Path | None = typer.Argument(None, help="Optional file or directory path to scope verification."),
    staged: bool = typer.Option(False, "--staged", help="Scope verification to staged git changes."),
    diff: str | None = typer.Option(None, "--diff", help="Scope verification to a named git diff range."),
) -> None:
    """Run the Litmus verification pipeline."""
    try:
        scope = resolve_verification_scope(
            Path.cwd(),
            explicit_paths=[target] if target is not None else None,
            staged=staged,
            diff=diff,
        )
    except (LookupError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None

    result = run_verification(Path.cwd(), scope=scope)
    save_replay_trace_records(Path.cwd(), result.replay_traces)
    typer.echo(render_verification_summary(result))

    has_breaking_replay = any(
        replay.classification is ReplayClassification.BREAKING_CHANGE
        for replay in result.replay_results
    )
    has_failed_property = any(
        property_result.status is PropertyCheckStatus.FAILED
        for property_result in result.property_results
    )
    if has_breaking_replay or has_failed_property:
        raise typer.Exit(code=1)


@app.command()
def watch() -> None:
    """Watch for changes and rerun Litmus verification."""
    try:
        run_watch(Path.cwd(), emit=typer.echo)
    except KeyboardInterrupt:
        typer.echo("Litmus watch stopped.")


@app.command()
def replay(seed: str = typer.Argument(..., help="Seed identifier to replay.")) -> None:
    """Replay a deterministic failing seed."""
    repo_root = Path.cwd()
    try:
        record = replay_record_for_seed(repo_root, seed)
    except FileNotFoundError:
        typer.echo("No replay traces found. Run `litmus verify` first.", err=True)
        raise typer.Exit(code=1) from None
    except LookupError:
        typer.echo(f"No replay trace found for {seed}.", err=True)
        raise typer.Exit(code=1) from None
    app = load_asgi_app(record.app_reference, repo_root)
    current_result = asyncio.run(
        run_asgi_app(
            app,
            method=record.method,
            path=record.path,
            json_body=record.request_payload,
            seed=record.seed_value,
        )
    )
    current_response = ResponseExample(
        status_code=current_result.status_code,
        json=current_result.body if isinstance(current_result.body, dict) else None,
    )
    baseline_response = ResponseExample(
        status_code=record.baseline_status_code,
        json=record.baseline_body,
    )
    scenario = Scenario(
        method=record.method,
        path=record.path,
        request=RequestExample(method=record.method, path=record.path, json=record.request_payload),
        expected_response=baseline_response,
    )

    async def runner(_: Scenario) -> ResponseExample:
        return current_response

    replay_results = asyncio.run(run_differential_replay([scenario], runner))
    classification = replay_results[0].classification if replay_results else ReplayClassification.UNCHANGED
    typer.echo(
        render_replay_summary(
            seed=record.seed,
            method=record.method,
            path=record.path,
            baseline_status_code=record.baseline_status_code,
            baseline_body=record.baseline_body,
            current_status_code=current_response.status_code,
            current_body=current_result.body,
            classification=classification,
            trace=current_result.trace,
        )
    )
