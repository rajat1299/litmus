from __future__ import annotations
from pathlib import Path

import typer

from litmus.dst.engine import run_verification
from litmus.errors import LitmusUserError
from litmus.init_flow import bootstrap_repo
from litmus.mcp import serve_mcp
from litmus.mcp.tools import run_replay_operation
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.reporting.console import render_verification_summary
from litmus.reporting.explanations import render_replay_explanation
from litmus.runs import RunMode, record_verification_run
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
        result = run_verification(Path.cwd(), scope=scope)
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None
    record_verification_run(Path.cwd(), result, mode=RunMode.LOCAL)
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
def mcp() -> None:
    """Run the Litmus MCP server over stdio."""
    serve_mcp(Path.cwd())


@app.command()
def replay(seed: str = typer.Argument(..., help="Seed identifier to replay.")) -> None:
    """Replay a deterministic failing seed."""
    repo_root = Path.cwd()
    try:
        replay_result = run_replay_operation(repo_root, seed, mode=RunMode.LOCAL)
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None
    typer.echo(render_replay_explanation(replay_result.explanation))
