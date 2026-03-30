from __future__ import annotations

import typer

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
    typer.echo("litmus verify is not implemented yet.")


@app.command()
def watch() -> None:
    """Watch for changes and rerun Litmus verification."""
    typer.echo("litmus watch is not implemented yet.")


@app.command()
def replay(seed: str = typer.Argument(..., help="Seed identifier to replay.")) -> None:
    """Replay a deterministic failing seed."""
    typer.echo(f"litmus replay is not implemented yet for {seed}.")
