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


def test_map_changed_code_to_endpoints_traces_relative_imports(tmp_path: Path) -> None:
    service_dir = tmp_path / "service"
    service_dir.mkdir()
    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "payments.py").write_text(
        """
async def charge_payment():
    return {"status": "charged"}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (service_dir / "api.py").write_text(
        """
from .payments import charge_payment


class FastAPI:
    def post(self, path):
        def decorator(func):
            return func

        return decorator


app = FastAPI()


@app.post("/charge")
async def charge_endpoint():
    return await charge_payment()
""".strip()
        + "\n",
        encoding="utf-8",
    )

    endpoints = map_changed_code_to_endpoints(
        tmp_path,
        ["service/payments.py"],
        changed_symbols={"service/payments.py": {"charge_payment"}},
    )

    assert [(endpoint.method, endpoint.path) for endpoint in endpoints] == [
        ("POST", "/charge"),
    ]


def test_map_changed_code_to_endpoints_traces_aliased_direct_imports(tmp_path: Path) -> None:
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    (services_dir / "__init__.py").write_text("", encoding="utf-8")
    (services_dir / "payments.py").write_text(
        """
async def charge_payment():
    return {"status": "charged"}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "api.py").write_text(
        """
from services.payments import charge_payment as charge


class FastAPI:
    def post(self, path):
        def decorator(func):
            return func

        return decorator


app = FastAPI()


@app.post("/charge")
async def charge_endpoint():
    return await charge()
""".strip()
        + "\n",
        encoding="utf-8",
    )

    endpoints = map_changed_code_to_endpoints(
        tmp_path,
        ["services/payments.py"],
        changed_symbols={"services/payments.py": {"charge_payment"}},
    )

    assert [(endpoint.method, endpoint.path) for endpoint in endpoints] == [
        ("POST", "/charge"),
    ]
