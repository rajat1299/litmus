from __future__ import annotations

import asyncio
from contextlib import contextmanager

import httpx

from litmus.simulators.base import HttpConnectionRefusedError, HttpTimeoutError
from litmus.simulators.http import HttpSimulator


@contextmanager
def patch_httpx(simulator: HttpSimulator):
    original_request = httpx.AsyncClient.request

    async def simulated_request(self, method, url, *args, **kwargs):
        try:
            response = await simulator.handle_request(
                method,
                str(url),
                supported_shape="httpx.AsyncClient",
            )
        except HttpTimeoutError as exc:
            raise httpx.ReadTimeout(str(exc)) from exc
        except HttpConnectionRefusedError as exc:
            raise httpx.ConnectError(str(exc)) from exc

        if response.latency_ms:
            await asyncio.sleep(response.latency_ms / 1000)

        request = httpx.Request(method=method, url=str(url))
        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            content=response.content_bytes(),
            request=request,
        )

    httpx.AsyncClient.request = simulated_request
    try:
        yield
    finally:
        httpx.AsyncClient.request = original_request
