from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from litmus.dst.faults import FaultPlan
from litmus.dst.runtime import RuntimeContext, TraceEvent


@dataclass(slots=True)
class AsgiExecutionResult:
    status_code: int
    body: Any
    trace: list[TraceEvent]


async def run_asgi_app(
    app,
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
    seed: int = 0,
    fault_plan: FaultPlan | None = None,
) -> AsgiExecutionResult:
    runtime = RuntimeContext(seed=seed, fault_plan=fault_plan or FaultPlan(seed=seed))
    request_body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": path,
        "headers": [(b"content-type", b"application/json")] if json_body is not None else [],
    }
    runtime.record(
        "request_started",
        seed=seed,
        method=scope["method"],
        path=path,
        fault_events=len(runtime.fault_plan.schedule),
    )

    receive_calls = 0
    response_status = 500
    response_headers: list[tuple[bytes, bytes]] = []
    response_chunks: list[bytes] = []

    async def receive() -> dict[str, Any]:
        nonlocal receive_calls
        if receive_calls == 0:
            receive_calls += 1
            return {
                "type": "http.request",
                "body": request_body,
                "more_body": False,
            }
        receive_calls += 1
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal response_status, response_headers
        if message["type"] == "http.response.start":
            response_status = message["status"]
            response_headers = message.get("headers", [])
            runtime.record("response_started", status_code=response_status)
            return

        if message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            response_chunks.append(chunk)
            runtime.record("response_body", bytes=len(chunk), more_body=message.get("more_body", False))

    await app(scope, receive, send)

    body = b"".join(response_chunks)
    runtime.record("request_completed", status_code=response_status)
    return AsgiExecutionResult(
        status_code=response_status,
        body=_decode_body(body, response_headers),
        trace=list(runtime.trace),
    )


def _decode_body(body: bytes, headers: list[tuple[bytes, bytes]]) -> Any:
    if not body:
        return None

    content_type = next(
        (
            value.decode("utf-8")
            for key, value in headers
            if key.lower() == b"content-type"
        ),
        "",
    )
    if "application/json" in content_type:
        return json.loads(body.decode("utf-8"))

    return body.decode("utf-8")
