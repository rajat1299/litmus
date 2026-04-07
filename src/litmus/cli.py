from __future__ import annotations
from pathlib import Path

import typer

from litmus.config import FaultProfile
from litmus.dst.engine import run_verification
from litmus.errors import LitmusUserError
from litmus.init_flow import bootstrap_repo
from litmus.invariants.models import InvariantStatus
from litmus.management import (
    accept_invariant,
    dismiss_invariant,
    list_invariant_reviews,
    list_invariants,
    set_config_value,
    set_invariant_status,
    show_invariant,
)
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification
from litmus.reporting.console import render_verification_summary
from litmus.reporting.explanations import render_replay_explanation
from litmus.runs import RunMode, record_verification_run
from litmus.surface import (
    CONFIG_GROUP_HELP,
    CONFIG_SET_OPERATION,
    ACCEPT_INVARIANT_OPERATION,
    DISMISS_INVARIANT_OPERATION,
    GROUNDED_ALPHA_TAGLINE,
    INIT_OPERATION,
    INVARIANTS_GROUP_HELP,
    LIST_INVARIANTS_OPERATION,
    MCP_OPERATION,
    REPLAY_OPERATION,
    REVIEW_INVARIANTS_GROUP_HELP,
    REVIEW_LIST_INVARIANTS_OPERATION,
    SET_INVARIANT_STATUS_OPERATION,
    SHOW_INVARIANT_OPERATION,
    VERIFY_OPERATION,
    WATCH_OPERATION,
)
from litmus.verify_scope import resolve_verification_scope
from litmus.watch import run_watch

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=GROUNDED_ALPHA_TAGLINE,
)
invariants_app = typer.Typer(no_args_is_help=True, help=INVARIANTS_GROUP_HELP)
review_app = typer.Typer(no_args_is_help=True, help=REVIEW_INVARIANTS_GROUP_HELP)
config_app = typer.Typer(no_args_is_help=True, help=CONFIG_GROUP_HELP)
app.add_typer(invariants_app, name="invariants")
invariants_app.add_typer(review_app, name="review")
app.add_typer(config_app, name="config")


@app.command(help=INIT_OPERATION.cli_help)
def init() -> None:
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


@app.command(help=VERIFY_OPERATION.cli_help)
def verify(
    target: Path | None = typer.Argument(None, help="Optional file or directory path to scope verification."),
    staged: bool = typer.Option(False, "--staged", help="Scope verification to staged git changes."),
    diff: str | None = typer.Option(None, "--diff", help="Scope verification to a named git diff range."),
) -> None:
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


@app.command(help=WATCH_OPERATION.cli_help)
def watch() -> None:
    try:
        run_watch(Path.cwd(), emit=typer.echo)
    except KeyboardInterrupt:
        typer.echo("Litmus watch stopped.")


@app.command(help=MCP_OPERATION.cli_help)
def mcp() -> None:
    from litmus.mcp.server import serve_mcp

    serve_mcp(Path.cwd())


@app.command(help=REPLAY_OPERATION.cli_help)
def replay(seed: str = typer.Argument(..., help="Seed identifier to replay.")) -> None:
    from litmus.mcp.tools import run_replay_operation

    repo_root = Path.cwd()
    try:
        replay_result = run_replay_operation(repo_root, seed, mode=RunMode.LOCAL)
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None
    typer.echo(render_replay_explanation(replay_result.explanation))


@invariants_app.command("list", help=LIST_INVARIANTS_OPERATION.cli_help)
def list_invariants_command() -> None:
    result = list_invariants(Path.cwd())
    typer.echo("Litmus invariants")
    typer.echo(f"Path: {result.invariants_path.relative_to(Path.cwd())}")
    typer.echo(f"Count: {len(result.invariants)}")
    for invariant in result.invariants:
        location = ""
        if invariant.method and invariant.path:
            location = f" {invariant.method.upper()} {invariant.path}"
        typer.echo(
            f"- {invariant.name} [{invariant.status.value}] {invariant.invariant_type}{location}"
        )


@review_app.command("list", help=REVIEW_LIST_INVARIANTS_OPERATION.cli_help)
def review_list_invariants_command(
    all_items: bool = typer.Option(False, "--all", help="Show all review states."),
    pending: bool = typer.Option(False, "--pending", help="Show pending suggested invariants."),
    dismissed: bool = typer.Option(False, "--dismissed", help="Show dismissed suggested invariants."),
    promoted: bool = typer.Option(False, "--promoted", help="Show promoted suggested invariants."),
) -> None:
    selected = [flag for flag in (all_items, pending, dismissed, promoted) if flag]
    if len(selected) > 1:
        typer.echo("Choose at most one review filter flag.", err=True)
        raise typer.Exit(code=1)

    if all_items:
        filter_name = "all"
    elif dismissed:
        filter_name = "dismissed"
    elif promoted:
        filter_name = "promoted"
    else:
        filter_name = "pending"

    try:
        result = list_invariant_reviews(Path.cwd(), filter_name=filter_name)
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None

    typer.echo("Litmus invariant review")
    typer.echo(f"Path: {result.invariants_path.relative_to(Path.cwd())}")
    typer.echo(f"Filter: {result.filter_name}")
    typer.echo(f"Count: {len(result.invariants)}")
    for invariant in result.invariants:
        location = ""
        if invariant.method and invariant.path:
            location = f" {invariant.method.upper()} {invariant.path}"
        typer.echo(
            f"- {invariant.name} [{invariant.status.value}] [{invariant.review_state.value}] "
            f"{invariant.invariant_type}{location}"
        )


@invariants_app.command("show", help=SHOW_INVARIANT_OPERATION.cli_help)
def show_invariant_command(name: str = typer.Argument(..., help="Invariant name to inspect.")) -> None:
    try:
        result = show_invariant(Path.cwd(), name)
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None

    invariant = result.invariant
    typer.echo(f"Name: {invariant.name}")
    typer.echo(f"Status: {invariant.status.value}")
    typer.echo(f"Type: {invariant.type.value}")
    typer.echo(f"Source: {invariant.source}")
    if invariant.request is not None and invariant.request.method and invariant.request.path:
        typer.echo(f"Request: {invariant.request.method.upper()} {invariant.request.path}")
    if invariant.response is not None and invariant.response.status_code is not None:
        typer.echo(f"Response: {invariant.response.status_code}")
    if invariant.review is not None:
        typer.echo(f"Review state: {invariant.review.state.value}")
        if invariant.review.reason is not None:
            typer.echo(f"Review reason: {invariant.review.reason}")
        if invariant.review.reviewed_at is not None:
            typer.echo(f"Reviewed at: {invariant.review.reviewed_at}")
        if invariant.review.review_source is not None:
            typer.echo(f"Review source: {invariant.review.review_source}")
        if invariant.review.review_run_id is not None:
            typer.echo(f"Review run: {invariant.review.review_run_id}")


@invariants_app.command("accept", help=ACCEPT_INVARIANT_OPERATION.cli_help)
def accept_invariant_command(
    name: str = typer.Argument(..., help="Suggested invariant name to accept."),
    reason: str | None = typer.Option(None, "--reason", help="Optional review reason to store."),
) -> None:
    try:
        result = accept_invariant(Path.cwd(), name=name, reason=reason)
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Accepted invariant {result.invariant.name} as confirmed.")


@invariants_app.command("dismiss", help=DISMISS_INVARIANT_OPERATION.cli_help)
def dismiss_invariant_command(
    name: str = typer.Argument(..., help="Suggested invariant name to dismiss."),
    reason: str = typer.Option(..., "--reason", help="Review reason to store."),
) -> None:
    try:
        result = dismiss_invariant(Path.cwd(), name=name, reason=reason)
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Dismissed suggested invariant {result.invariant.name}.")


@invariants_app.command("set-status", help=SET_INVARIANT_STATUS_OPERATION.cli_help)
def set_invariant_status_command(
    name: str = typer.Argument(..., help="Invariant name to update."),
    confirmed: bool = typer.Option(False, "--confirmed", help="Mark the invariant as confirmed."),
    suggested: bool = typer.Option(False, "--suggested", help="Mark the invariant as suggested."),
) -> None:
    if confirmed == suggested:
        typer.echo("Choose exactly one status flag: --confirmed or --suggested.", err=True)
        raise typer.Exit(code=1)

    status = InvariantStatus.CONFIRMED if confirmed else InvariantStatus.SUGGESTED
    try:
        result = set_invariant_status(Path.cwd(), name=name, status=status)
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Updated invariant {result.invariant.name} to {result.invariant.status.value}.")


@config_app.command("set", help=CONFIG_SET_OPERATION.cli_help)
def config_set_command(
    key: str = typer.Argument(..., help="Config key to write."),
    value: str = typer.Argument(..., help="Config value to write."),
) -> None:
    try:
        result = set_config_value(Path.cwd(), key=key, value=value)
    except ValueError:
        valid_profiles = ", ".join(profile.value for profile in FaultProfile)
        typer.echo(f"Unsupported fault profile. Use one of: {valid_profiles}.", err=True)
        raise typer.Exit(code=1) from None
    except LitmusUserError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Set {result.key} = {result.value}")
