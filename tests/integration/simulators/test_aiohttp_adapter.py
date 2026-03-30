from __future__ import annotations

import asyncio

import aiohttp

from litmus.simulators.aiohttp_adapter import patch_aiohttp
from litmus.simulators.http import HttpSimulator


def test_patch_aiohttp_intercepts_requests_and_restores_original_behavior() -> None:
    simulator = HttpSimulator()
    simulator.add_json_response(
        method="GET",
        url_pattern="https://api.example.com/orders/*",
        status_code=200,
        json_body={"status": "ok"},
    )

    async def exercise() -> None:
        async with aiohttp.ClientSession() as session:
            with patch_aiohttp(simulator):
                async with session.get("https://api.example.com/orders/123") as response:
                    assert response.status == 200
                    assert await response.json() == {"status": "ok"}

            try:
                async with session.get("https://api.example.com/orders/123", timeout=0.1):
                    pass
            except Exception:
                return
            raise AssertionError("expected real client behavior to be restored after unpatch")

    asyncio.run(exercise())
