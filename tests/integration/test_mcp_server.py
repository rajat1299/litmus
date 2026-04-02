from __future__ import annotations

import asyncio
from pathlib import Path
import textwrap

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_litmus_mcp_server_exposes_structured_verify_replay_explain_and_list_tools(tmp_path: Path) -> None:
    repo_root = _build_breaking_verify_repo(tmp_path)

    async def exercise_server() -> None:
        server = StdioServerParameters(command="litmus", args=["mcp"], cwd=str(repo_root))
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                tool_names = {tool.name for tool in tools.tools}
                assert {"verify", "replay", "explain_failure", "list_invariants"} <= tool_names

                verify_result = await session.call_tool("verify", arguments={})
                verify_payload = verify_result.structuredContent
                assert verify_payload["app_reference"] == "service.app:app"
                assert verify_payload["replay"]["breaking"] == 3
                assert verify_payload["run_id"].startswith("run-")

                invariants_result = await session.call_tool("list_invariants", arguments={})
                invariants_payload = invariants_result.structuredContent
                assert invariants_payload["total"] == 1
                assert invariants_payload["invariants"][0]["name"] == "health_returns_200"

                replay_result = await session.call_tool("replay", arguments={"seed": "seed:1"})
                replay_payload = replay_result.structuredContent
                assert replay_payload["seed"] == "seed:1"
                assert replay_payload["explanation"]["classification"] == "breaking_change"
                assert replay_payload["run_id"].startswith("run-")

                explain_result = await session.call_tool("explain_failure", arguments={"seed": "seed:1"})
                explain_payload = explain_result.structuredContent
                assert explain_payload["seed"] == "seed:1"
                assert explain_payload["explanation"]["classification"] == "breaking_change"
                assert explain_payload["source_run_id"] == replay_payload["source_run_id"]

    asyncio.run(exercise_server())


def test_litmus_mcp_server_observes_repo_edits_across_repeated_verify_calls(tmp_path: Path) -> None:
    repo_root = _build_verify_repo(tmp_path)

    async def exercise_server() -> None:
        server = StdioServerParameters(command="litmus", args=["mcp"], cwd=str(repo_root))
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                first_result = await session.call_tool("verify", arguments={})
                first_payload = first_result.structuredContent
                assert first_payload["replay"]["unchanged"] == 3
                assert first_payload["replay"]["breaking"] == 0

                _rewrite_health_app(
                    repo_root / "service" / "app.py",
                    status_code=500,
                    status_value="broken",
                )

                second_result = await session.call_tool("verify", arguments={})
                second_payload = second_result.structuredContent
                assert second_payload["replay"]["unchanged"] == 0
                assert second_payload["replay"]["breaking"] == 3

    asyncio.run(exercise_server())


def _build_verify_repo(repo_root: Path) -> Path:
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def get(self, path: str):
                    def decorator(func):
                        self.routes[("GET", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler()
                    await send(
                        {
                            "type": "http.response.start",
                            "status": response["status_code"],
                            "headers": [(b"content-type", b"application/json")],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": json.dumps(response["json"]).encode("utf-8"),
                        }
                    )


            app = FastAPI()


            @app.get("/health")
            async def health():
                return {"status_code": 200, "json": {"status": "ok"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tests_dir / "test_health.py").write_text(
        textwrap.dedent(
            """
            def test_health_returns_200():
                request = {
                    "method": "GET",
                    "path": "/health",
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "ok"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return repo_root


def _build_breaking_verify_repo(repo_root: Path) -> Path:
    repo_root = _build_verify_repo(repo_root)
    _rewrite_health_app(
        repo_root / "service" / "app.py",
        status_code=500,
        status_value="broken",
    )
    return repo_root


def _rewrite_health_app(app_path: Path, *, status_code: int, status_value: str) -> None:
    app_path.write_text(
        app_path.read_text(encoding="utf-8")
        .replace(
            'return {"status_code": 200, "json": {"status": "ok"}}',
            f'return {{"status_code": {status_code}, "json": {{"status": "{status_value}"}}}}',
        )
        .replace(
            'return {"status_code": 500, "json": {"status": "broken"}}',
            f'return {{"status_code": {status_code}, "json": {{"status": "{status_value}"}}}}',
        ),
        encoding="utf-8",
    )
