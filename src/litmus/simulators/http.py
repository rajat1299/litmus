from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any

from litmus.dst.faults import FaultPlan
from litmus.simulators.base import (
    HttpConnectionRefusedError,
    HttpTimeoutError,
    SimulatedHttpResponse,
)


@dataclass(slots=True)
class _HttpFixture:
    method: str
    url_pattern: str
    response: SimulatedHttpResponse


class HttpSimulator:
    def __init__(
        self,
        fault_plan: FaultPlan | None = None,
        record_event: Callable[[str, Any], None] | None = None,
    ) -> None:
        self._fixtures: list[_HttpFixture] = []
        self._fault_plan = fault_plan or FaultPlan(seed=0)
        self._request_step = 0
        self._record_event = record_event

    def add_json_response(
        self,
        method: str,
        url_pattern: str,
        status_code: int,
        json_body,
        headers: dict[str, str] | None = None,
    ) -> None:
        response_headers = {"content-type": "application/json"}
        if headers:
            response_headers.update(headers)
        self._fixtures.append(
            _HttpFixture(
                method=method.upper(),
                url_pattern=url_pattern,
                response=SimulatedHttpResponse(
                    status_code=status_code,
                    headers=response_headers,
                    json_body=json_body,
                ),
            )
        )

    async def handle_request(
        self,
        method: str,
        url: str,
        *,
        supported_shape: str = "httpx/aiohttp",
    ) -> SimulatedHttpResponse:
        self._request_step += 1
        self._record("boundary_detected", boundary="http")
        self._record("boundary_intercepted", boundary="http", supported_shape=supported_shape)
        self._record("boundary_simulated", boundary="http")
        self._record("http_request_started", step=self._request_step, method=method.upper(), url=url)
        fault = self._fault_plan.fault_for_step(self._request_step)
        fixture = self._match_fixture(method, url)

        if fault is not None and fault.target in {"http", "httpx", "aiohttp"}:
            self._record(
                "fault_injected",
                step=self._request_step,
                target=fault.target,
                fault_kind=fault.kind,
                params=dict(fault.params),
                url=url,
            )
            if fault.kind == "timeout":
                raise HttpTimeoutError(f"simulated timeout for {method.upper()} {url}")
            if fault.kind == "connection_refused":
                raise HttpConnectionRefusedError(f"simulated connection refusal for {method.upper()} {url}")
            if fault.kind == "http_error":
                status_code = int(fault.params.get("status_code", 500))
                return SimulatedHttpResponse(
                    status_code=status_code,
                    headers={"content-type": "application/json"},
                    json_body={"error": "simulated http error"},
                )
            if fault.kind == "slow_response":
                response = fixture.response if fixture is not None else self._default_response(method, url)
                return SimulatedHttpResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    json_body=response.json_body,
                    text_body=response.text_body,
                    latency_ms=int(fault.params.get("delay_ms", 0)),
                )

        if fixture is None:
            return self._default_response(method, url)

        return SimulatedHttpResponse(
            status_code=fixture.response.status_code,
            headers=dict(fixture.response.headers),
            json_body=fixture.response.json_body,
            text_body=fixture.response.text_body,
            latency_ms=fixture.response.latency_ms,
        )

    def _record(self, event_kind: str, **metadata: Any) -> None:
        if self._record_event is not None:
            self._record_event(event_kind, **metadata)

    def _default_response(self, method: str, url: str) -> SimulatedHttpResponse:
        self._record(
            "http_response_defaulted",
            step=self._request_step,
            method=method.upper(),
            url=url,
        )
        return SimulatedHttpResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            json_body={},
        )

    def _match_fixture(self, method: str, url: str) -> _HttpFixture | None:
        normalized_method = method.upper()
        for fixture in self._fixtures:
            if fixture.method == normalized_method and fnmatch(url, fixture.url_pattern):
                return fixture
        return None
