from __future__ import annotations

from pathlib import Path

from litmus.discovery.routes import extract_routes


def test_extract_routes_reads_http_method_and_path() -> None:
    fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "apps" / "payment_service"

    routes = extract_routes(fixture_root / "app.py", fixture_root)

    assert [
        (route.method, route.path, route.handler_name)
        for route in routes
    ] == [
        ("POST", "/payments/charge", "charge_endpoint"),
        ("POST", "/payments/refund", "refund_endpoint"),
        ("GET", "/health", "health_check"),
    ]
