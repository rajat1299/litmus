from __future__ import annotations

from pathlib import Path

from litmus.discovery.tracing import map_changed_code_to_endpoints


def test_map_changed_code_to_endpoints_returns_routes_for_changed_handler_file() -> None:
    fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "apps" / "payment_service"

    endpoints = map_changed_code_to_endpoints(fixture_root, ["app.py"])

    assert {(endpoint.method, endpoint.path) for endpoint in endpoints} == {
        ("POST", "/payments/charge"),
        ("POST", "/payments/refund"),
        ("GET", "/health"),
    }


def test_map_changed_code_to_endpoints_traces_imported_symbol_usage() -> None:
    fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "apps" / "payment_service"

    endpoints = map_changed_code_to_endpoints(
        fixture_root,
        ["services/payments.py"],
        changed_symbols={"services/payments.py": {"charge_payment"}},
    )

    assert [(endpoint.method, endpoint.path) for endpoint in endpoints] == [
        ("POST", "/payments/charge"),
    ]
