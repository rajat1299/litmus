from __future__ import annotations

import asyncio

import aiohttp

from litmus.dst.faults import FaultPlan, FaultSpec
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


def test_patch_aiohttp_preserves_client_response_transparency() -> None:
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
                    assert isinstance(response, aiohttp.ClientResponse)
                    assert response.status == 200
                    assert response.headers["content-type"] == "application/json"
                    assert await response.json() == {"status": "ok"}
                    assert await response.text() == '{"status": "ok"}'
                    assert await response.read() == b'{"status": "ok"}'

    asyncio.run(exercise())


def test_patch_aiohttp_applies_slow_response_delay() -> None:
    simulator = HttpSimulator(
        fault_plan=FaultPlan(
            seed=11,
            schedule={
                1: FaultSpec(kind="slow_response", target="aiohttp", params={"delay_ms": 50}),
            },
        )
    )
    simulator.add_json_response(
        method="GET",
        url_pattern="https://api.example.com/orders/*",
        status_code=200,
        json_body={"status": "ok"},
    )

    async def exercise() -> None:
        async with aiohttp.ClientSession() as session:
            with patch_aiohttp(simulator):
                start = asyncio.get_running_loop().time()
                async with session.get("https://api.example.com/orders/123") as response:
                    elapsed = asyncio.get_running_loop().time() - start
                    assert response.status == 200

        assert elapsed >= 0.04

    asyncio.run(exercise())
