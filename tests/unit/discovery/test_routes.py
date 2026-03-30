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


def test_extract_routes_emits_all_methods_for_route_decorator(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
class Router:
    def route(self, path, methods=None):
        def decorator(func):
            return func

        return decorator


app = Router()


@app.route("/items", methods=["GET", "POST"])
async def items():
    return {}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    routes = extract_routes(app_file, tmp_path)

    assert [(route.method, route.path, route.handler_name) for route in routes] == [
        ("GET", "/items", "items"),
        ("POST", "/items", "items"),
    ]
