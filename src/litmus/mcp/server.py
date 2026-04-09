from __future__ import annotations

from functools import partial
from pathlib import Path

import anyio
from mcp.server.fastmcp import FastMCP

from litmus.mcp.tools import (
    run_explain_failure_operation,
    run_list_invariants_operation,
    run_replay_operation,
    run_verify_operation,
)
from litmus.mcp.types import (
    ExplainFailureOperationPayload,
    ListInvariantsOperationPayload,
    ReplayOperationPayload,
    VerifyOperationPayload,
)
from litmus.surface import (
    EXPLAIN_FAILURE_OPERATION,
    LIST_INVARIANTS_OPERATION,
    MCP_SERVER_INSTRUCTIONS,
    REPLAY_OPERATION,
    VERIFY_OPERATION,
)


def build_mcp_server(root: Path | None = None) -> FastMCP:
    server = FastMCP(
        name="litmus",
        instructions=MCP_SERVER_INSTRUCTIONS,
    )
    workspace_root = Path.cwd() if root is None else Path(root)

    @server.tool(name="verify", description=VERIFY_OPERATION.mcp_description, structured_output=True)
    async def verify(
        target: str | None = None,
        staged: bool = False,
        diff: str | None = None,
        decision_policy: str | None = None,
    ) -> VerifyOperationPayload:
        result = await anyio.to_thread.run_sync(
            partial(
                run_verify_operation,
                workspace_root,
                target=target,
                staged=staged,
                diff=diff,
                decision_policy=decision_policy,
            )
        )
        return VerifyOperationPayload.from_operation(result)

    @server.tool(
        name="list_invariants",
        description=LIST_INVARIANTS_OPERATION.mcp_description,
        structured_output=True,
    )
    async def list_invariants(
        target: str | None = None,
        staged: bool = False,
        diff: str | None = None,
    ) -> ListInvariantsOperationPayload:
        result = await anyio.to_thread.run_sync(
            partial(
                run_list_invariants_operation,
                workspace_root,
                target=target,
                staged=staged,
                diff=diff,
            )
        )
        return ListInvariantsOperationPayload.from_operation(result)

    @server.tool(
        name="replay",
        description=REPLAY_OPERATION.mcp_description,
        structured_output=True,
    )
    async def replay(seed: str) -> ReplayOperationPayload:
        result = await anyio.to_thread.run_sync(partial(run_replay_operation, workspace_root, seed))
        return ReplayOperationPayload.from_operation(result)

    @server.tool(
        name="explain_failure",
        description=EXPLAIN_FAILURE_OPERATION.mcp_description,
        structured_output=True,
    )
    async def explain_failure(seed: str) -> ExplainFailureOperationPayload:
        result = await anyio.to_thread.run_sync(
            partial(run_explain_failure_operation, workspace_root, seed)
        )
        return ExplainFailureOperationPayload.from_operation(result)

    return server


def serve_mcp(root: Path | None = None) -> None:
    build_mcp_server(root).run(transport="stdio")
