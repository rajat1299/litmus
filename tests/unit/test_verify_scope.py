from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from litmus.discovery.routes import RouteDefinition
from litmus.invariants.models import Invariant, InvariantStatus, InvariantType, RequestExample, ResponseExample
from litmus.verify_scope import apply_verification_scope, resolve_verification_scope


def test_resolve_verification_scope_defaults_to_full_repo(tmp_path: Path) -> None:
    scope = resolve_verification_scope(tmp_path)

    assert scope.mode == "full"
    assert scope.changed_files == []
    assert scope.label == "full repo"


def test_resolve_verification_scope_normalizes_explicit_paths_relative_to_repo(tmp_path: Path) -> None:
    service_dir = tmp_path / "service"
    service_dir.mkdir()
    target_file = service_dir / "payments.py"
    target_file.write_text("", encoding="utf-8")

    scope = resolve_verification_scope(tmp_path, explicit_paths=[target_file])

    assert scope.mode == "paths"
    assert scope.changed_files == ["service/payments.py"]
    assert scope.label == "paths: service/payments.py"


def test_resolve_verification_scope_rejects_conflicting_modes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Choose exactly one verification scope mode"):
        resolve_verification_scope(tmp_path, explicit_paths=[tmp_path], staged=True)


def test_apply_verification_scope_filters_routes_and_invariants_for_changed_code(tmp_path: Path) -> None:
    service_dir = tmp_path / "service"
    service_dir.mkdir()
    (service_dir / "__init__.py").write_text("", encoding="utf-8")
    (service_dir / "payments.py").write_text(
        """
async def charge_payment(payload):
    return {"status": "charged"}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (service_dir / "refunds.py").write_text(
        """
async def refund_payment(payload):
    return {"status": "refunded"}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from service.payments import charge_payment
            from service.refunds import refund_payment


            class FastAPI:
                def post(self, path):
                    def decorator(func):
                        return func

                    return decorator


            app = FastAPI()


            @app.post("/payments/charge")
            async def charge(payload):
                return await charge_payment(payload)


            @app.post("/payments/refund")
            async def refund(payload):
                return await refund_payment(payload)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    routes = [
        RouteDefinition(method="POST", path="/payments/charge", handler_name="charge", file_path="service/app.py"),
        RouteDefinition(method="POST", path="/payments/refund", handler_name="refund", file_path="service/app.py"),
    ]
    invariants = [
        Invariant(
            name="charge",
            source="mined:tests/test_payments.py::test_charge",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
            response=ResponseExample(status_code=200, json={"status": "charged"}),
        ),
        Invariant(
            name="refund",
            source="mined:tests/test_refunds.py::test_refund",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/refund", json={"id": "r-1"}),
            response=ResponseExample(status_code=200, json={"status": "refunded"}),
        ),
    ]
    scope = resolve_verification_scope(tmp_path, explicit_paths=[service_dir / "refunds.py"])

    scoped_routes, scoped_invariants = apply_verification_scope(tmp_path, routes, invariants, scope)

    assert [(route.method, route.path) for route in scoped_routes] == [("POST", "/payments/refund")]
    assert [invariant.name for invariant in scoped_invariants] == ["refund"]


def test_apply_verification_scope_selects_changed_test_file_invariants(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    changed_test_file = tests_dir / "test_refunds.py"
    changed_test_file.write_text("", encoding="utf-8")

    routes = [
        RouteDefinition(method="POST", path="/payments/charge", handler_name="charge", file_path="service/app.py"),
        RouteDefinition(method="POST", path="/payments/refund", handler_name="refund", file_path="service/app.py"),
    ]
    invariants = [
        Invariant(
            name="charge",
            source="mined:tests/test_payments.py::test_charge",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
            response=ResponseExample(status_code=200, json={"status": "charged"}),
        ),
        Invariant(
            name="refund",
            source="mined:tests/test_refunds.py::test_refund",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/refund", json={"id": "r-1"}),
            response=ResponseExample(status_code=200, json={"status": "refunded"}),
        ),
    ]
    scope = resolve_verification_scope(tmp_path, explicit_paths=[changed_test_file])

    scoped_routes, scoped_invariants = apply_verification_scope(tmp_path, routes, invariants, scope)

    assert [(route.method, route.path) for route in scoped_routes] == [("POST", "/payments/refund")]
    assert [invariant.name for invariant in scoped_invariants] == ["refund"]


def test_apply_verification_scope_matches_absolute_mined_test_sources(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    changed_test_file = tests_dir / "test_refunds.py"
    changed_test_file.write_text("", encoding="utf-8")

    routes = [
        RouteDefinition(method="POST", path="/payments/charge", handler_name="charge", file_path="service/app.py"),
        RouteDefinition(method="POST", path="/payments/refund", handler_name="refund", file_path="service/app.py"),
    ]
    invariants = [
        Invariant(
            name="charge",
            source=f"mined:{(tests_dir / 'test_payments.py').as_posix()}::test_charge",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/charge", json={"amount": 100}),
            response=ResponseExample(status_code=200, json={"status": "charged"}),
        ),
        Invariant(
            name="refund",
            source=f"mined:{changed_test_file.as_posix()}::test_refund",
            status=InvariantStatus.CONFIRMED,
            type=InvariantType.DIFFERENTIAL,
            request=RequestExample(method="POST", path="/payments/refund", json={"id": "r-1"}),
            response=ResponseExample(status_code=200, json={"status": "refunded"}),
        ),
    ]
    scope = resolve_verification_scope(tmp_path, explicit_paths=[changed_test_file])

    scoped_routes, scoped_invariants = apply_verification_scope(tmp_path, routes, invariants, scope)

    assert [(route.method, route.path) for route in scoped_routes] == [("POST", "/payments/refund")]
    assert [invariant.name for invariant in scoped_invariants] == ["refund"]
