from __future__ import annotations

import json
from typing import Any


class FastAPI:
    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Any] = {}

    def post(self, path: str):
        def decorator(func):
            self.routes[("POST", path)] = func
            return func

        return decorator

    async def __call__(self, scope, receive, send) -> None:
        request = await receive()
        payload = json.loads(request["body"].decode("utf-8")) if request["body"] else None
        handler = self.routes[(scope["method"], scope["path"])]
        response = await handler(payload)
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


async def charge_with_retry(payload: dict[str, Any] | None) -> dict[str, Any]:
    amount = int((payload or {}).get("amount", 0))
    if amount > 500:
        return {"status_code": 402, "json": {"status": "declined"}}

    # Intentional regression for the alpha demo: the retry path returns a server
    # error instead of the mined success contract for the happy-path charge flow.
    return {"status_code": 500, "json": {"status": "duplicate_charge_risk"}}


@app.post("/payments/charge")
async def charge(payload: dict[str, Any] | None) -> dict[str, Any]:
    return await charge_with_retry(payload)
