from __future__ import annotations

import asyncio

from litmus.dst.faults import FaultPlan, FaultSpec
from litmus.simulators.http import (
    HttpConnectionRefusedError,
    HttpSimulator,
    HttpTimeoutError,
)


def test_http_simulator_matches_url_patterns_and_returns_fixture_payload() -> None:
    simulator = HttpSimulator()
    simulator.add_json_response(
        method="GET",
        url_pattern="https://api.example.com/orders/*",
        status_code=200,
        json_body={"status": "ok"},
    )

    response = asyncio.run(
        simulator.handle_request("GET", "https://api.example.com/orders/123"),
    )

    assert response.status_code == 200
    assert response.json_body == {"status": "ok"}
    assert response.latency_ms == 0


def test_http_simulator_applies_timeout_connection_refusal_http_error_and_slow_response() -> None:
    simulator = HttpSimulator(
        fault_plan=FaultPlan(
            seed=7,
            schedule={
                1: FaultSpec(kind="timeout", target="http"),
                2: FaultSpec(kind="connection_refused", target="http"),
                3: FaultSpec(kind="http_error", target="http", params={"status_code": 500}),
                4: FaultSpec(kind="slow_response", target="http", params={"delay_ms": 250}),
            },
        )
    )
    simulator.add_json_response(
        method="GET",
        url_pattern="https://api.example.com/orders/*",
        status_code=200,
        json_body={"status": "ok"},
    )

    try:
        asyncio.run(simulator.handle_request("GET", "https://api.example.com/orders/1"))
    except HttpTimeoutError:
        pass
    else:
        raise AssertionError("expected timeout fault")

    try:
        asyncio.run(simulator.handle_request("GET", "https://api.example.com/orders/2"))
    except HttpConnectionRefusedError:
        pass
    else:
        raise AssertionError("expected connection refusal fault")

    http_error = asyncio.run(simulator.handle_request("GET", "https://api.example.com/orders/3"))
    slow_response = asyncio.run(simulator.handle_request("GET", "https://api.example.com/orders/4"))

    assert http_error.status_code == 500
    assert slow_response.status_code == 200
    assert slow_response.latency_ms == 250
