from __future__ import annotations

import asyncio
import json

from litmus.dst.asgi import run_asgi_app
from litmus.dst.faults import FaultPlan


def test_run_asgi_app_captures_status_body_and_trace() -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        message = await receive()
        payload = json.loads(message["body"].decode("utf-8"))

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps(
                    {"status": "charged", "amount": payload["amount"]},
                ).encode("utf-8"),
            }
        )

    result = asyncio.run(
        run_asgi_app(
            app=app,
            method="POST",
            path="/payments/charge",
            json_body={"amount": 100},
            seed=7,
            fault_plan=FaultPlan(seed=7),
        )
    )

    assert result.status_code == 200
    assert result.body == {"status": "charged", "amount": 100}
    assert [event.kind for event in result.trace] == [
        "request_started",
        "response_started",
        "response_body",
        "request_completed",
    ]
    assert result.trace[0].metadata["seed"] == 7


def test_run_asgi_app_does_not_invent_client_disconnect_after_request_body() -> None:
    async def app(scope, receive, send):
        first_message = await receive()
        second_message = await receive()

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps(
                    {
                        "first_type": first_message["type"],
                        "second_type": second_message["type"],
                        "second_body": second_message.get("body", b"").decode("utf-8"),
                    }
                ).encode("utf-8"),
            }
        )

    result = asyncio.run(
        run_asgi_app(
            app=app,
            method="POST",
            path="/payments/charge",
            json_body={"amount": 100},
            seed=7,
            fault_plan=FaultPlan(seed=7),
        )
    )

    assert result.body == {
        "first_type": "http.request",
        "second_type": "http.request",
        "second_body": "",
    }


def test_run_asgi_app_preserves_plain_text_response_body() -> None:
    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"123",
            }
        )

    result = asyncio.run(
        run_asgi_app(
            app=app,
            method="GET",
            path="/plain",
            seed=3,
            fault_plan=FaultPlan(seed=3),
        )
    )

    assert result.status_code == 200
    assert result.body == "123"
