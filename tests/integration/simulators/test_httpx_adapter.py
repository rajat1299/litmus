from __future__ import annotations

import asyncio

import httpx

from litmus.dst.faults import FaultPlan, FaultSpec
from litmus.simulators.http import HttpSimulator
from litmus.simulators.httpx_adapter import patch_httpx


def test_patch_httpx_intercepts_requests_and_restores_original_behavior() -> None:
    simulator = HttpSimulator()
    simulator.add_json_response(
        method="GET",
        url_pattern="https://api.example.com/orders/*",
        status_code=200,
        json_body={"status": "ok"},
    )

    async def exercise() -> None:
        async with httpx.AsyncClient() as client:
            with patch_httpx(simulator):
                response = await client.get("https://api.example.com/orders/123")
                assert response.status_code == 200
                assert response.json() == {"status": "ok"}

            try:
                await client.get("https://api.example.com/orders/123", timeout=0.1)
            except Exception:
                return
            raise AssertionError("expected real client behavior to be restored after unpatch")

    asyncio.run(exercise())


def test_patch_httpx_applies_slow_response_delay() -> None:
    simulator = HttpSimulator(
        fault_plan=FaultPlan(
            seed=11,
            schedule={
                1: FaultSpec(kind="slow_response", target="httpx", params={"delay_ms": 50}),
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
        async with httpx.AsyncClient() as client:
            with patch_httpx(simulator):
                start = asyncio.get_running_loop().time()
                response = await client.get("https://api.example.com/orders/123")
                elapsed = asyncio.get_running_loop().time() - start

        assert response.status_code == 200
        assert elapsed >= 0.04

    asyncio.run(exercise())
