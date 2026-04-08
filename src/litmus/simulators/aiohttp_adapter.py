from __future__ import annotations

import asyncio
from contextlib import contextmanager
import json

import aiohttp
from multidict import CIMultiDict, CIMultiDictProxy

from litmus.simulators.base import HttpConnectionRefusedError, HttpTimeoutError, SimulatedHttpResponse
from litmus.simulators.http import HttpSimulator


class _BaseSimulatedAiohttpResponse:
    __slots__ = ("_headers", "_response")

    def __init__(self, response: SimulatedHttpResponse) -> None:
        self._response = response
        self._headers = CIMultiDictProxy(CIMultiDict(response.headers))

    @property
    def status(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> CIMultiDictProxy[str]:
        return self._headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        if self._response.json_body is not None:
            return self._response.json_body
        return json.loads(await self.text())

    async def text(self):
        return self._response.content_bytes().decode("utf-8")

    async def read(self):
        return self._response.content_bytes()

    def release(self) -> None:
        return None

    def close(self) -> None:
        return None

    async def wait_for_close(self) -> None:
        return None


def _build_patched_aiohttp_response_class(original_response_class):
    class _PatchedAiohttpResponse(_BaseSimulatedAiohttpResponse, original_response_class):
        __slots__ = ()

    return _PatchedAiohttpResponse


@contextmanager
def patch_aiohttp(simulator: HttpSimulator):
    original_request = aiohttp.ClientSession._request
    original_response_class = getattr(aiohttp, "ClientResponse", None)
    patched_response_class = (
        _build_patched_aiohttp_response_class(original_response_class)
        if isinstance(original_response_class, type)
        else _BaseSimulatedAiohttpResponse
    )

    async def simulated_request(self, method, url, *args, **kwargs):
        try:
            response = await simulator.handle_request(
                method,
                str(url),
                supported_shape="aiohttp.ClientSession",
            )
        except HttpTimeoutError as exc:
            raise asyncio.TimeoutError(str(exc)) from exc
        except HttpConnectionRefusedError as exc:
            raise aiohttp.ClientConnectionError(str(exc)) from exc

        if response.latency_ms:
            await asyncio.sleep(response.latency_ms / 1000)

        return patched_response_class(response)

    aiohttp.ClientSession._request = simulated_request
    try:
        yield
    finally:
        aiohttp.ClientSession._request = original_request
