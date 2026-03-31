from __future__ import annotations

from pathlib import Path

import typer

from litmus.dst.engine import run_verification
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.reporting.console import render_verification_summary

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Deterministic fault-injection verification for agent-written code.",
)


@app.command()
def init() -> None:
    """Bootstrap Litmus in the current repository."""
    typer.echo("litmus init is not implemented yet.")


@app.command()
def verify() -> None:
    """Run the Litmus verification pipeline."""
    result = run_verification(Path.cwd())
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
    typer.echo("litmus watch is not implemented yet.")


@app.command()
def replay(seed: str = typer.Argument(..., help="Seed identifier to replay.")) -> None:
    """Replay a deterministic failing seed."""
    typer.echo(f"litmus replay is not implemented yet for {seed}.")
