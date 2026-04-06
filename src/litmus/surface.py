from __future__ import annotations

from dataclasses import dataclass


GROUNDED_ALPHA_TAGLINE = "Grounded alpha verification for Python async ASGI services."
GROUNDED_ALPHA_SURFACE_LABEL = "grounded alpha for Python async ASGI services"
GROUNDED_ALPHA_SURFACE_SHORT_LABEL = "Python async ASGI services"


@dataclass(frozen=True, slots=True)
class OperationSurface:
    cli_help: str
    mcp_description: str


INIT_OPERATION = OperationSurface(
    cli_help="Bootstrap Litmus in the current repository using the grounded alpha path.",
    mcp_description="",
)

VERIFY_OPERATION = OperationSurface(
    cli_help="Run grounded Litmus alpha verification for the current scope.",
    mcp_description=(
        "Run grounded Litmus alpha verification for the selected workspace scope "
        "and persist a replayable local run."
    ),
)

WATCH_OPERATION = OperationSurface(
    cli_help="Watch local Python and config changes and rerun grounded Litmus verification.",
    mcp_description="",
)

MCP_OPERATION = OperationSurface(
    cli_help="Run the local Litmus MCP server over stdio.",
    mcp_description="",
)

REPLAY_OPERATION = OperationSurface(
    cli_help="Replay a recorded seed from the latest replayable Litmus run.",
    mcp_description=(
        "Replay a stored seed from the latest replayable Litmus run and return a structured explanation."
    ),
)

INVARIANTS_GROUP_HELP = "Inspect and update curated Litmus invariant records."
CONFIG_GROUP_HELP = "Set grounded Litmus repository configuration values."

LIST_INVARIANTS_OPERATION = OperationSurface(
    cli_help="List curated Litmus invariants from the local invariant store.",
    mcp_description="List confirmed and suggested invariants visible in the selected grounded verification scope.",
)

SHOW_INVARIANT_OPERATION = OperationSurface(
    cli_help="Show one curated Litmus invariant from the local invariant store.",
    mcp_description="",
)

SET_INVARIANT_STATUS_OPERATION = OperationSurface(
    cli_help="Set the status of one curated Litmus invariant.",
    mcp_description="",
)

CONFIG_SET_OPERATION = OperationSurface(
    cli_help="Set one grounded Litmus repository config value.",
    mcp_description="",
)

EXPLAIN_FAILURE_OPERATION = OperationSurface(
    cli_help="",
    mcp_description=(
        "Explain a stored seed from the latest replayable Litmus run without creating a new replay run."
    ),
)

MCP_SERVER_INSTRUCTIONS = (
    "Use this local stdio Litmus alpha server to run grounded verification, "
    "replay stored seeds from the latest replayable run, and inspect visible invariants."
)
