from __future__ import annotations

import textwrap

from litmus.init_flow import bootstrap_repo
from litmus.invariants.store import load_invariants


def test_bootstrap_repo_creates_config_and_mined_invariants_for_asgi_repo(tmp_path) -> None:
    service_dir = tmp_path / "service"
    tests_dir = tmp_path / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def post(self, path: str):
                    def decorator(func):
                        self.routes[("POST", path)] = func
                        return func

                    return decorator


            app = FastAPI()


            @app.post("/payments/charge")
            async def charge(payload):
                return {"status": "ok"}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tests_dir / "test_payments.py").write_text(
        textwrap.dedent(
            """
            def test_charge_returns_200_on_success():
                request = {
                    "method": "POST",
                    "path": "/payments/charge",
                    "json": {"amount": 100},
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "charged"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = bootstrap_repo(tmp_path)

    assert result.app_reference == "service.app:app"
    assert result.config_path == tmp_path / "litmus.yaml"
    assert result.invariants_path == tmp_path / ".litmus" / "invariants.yaml"
    assert result.config_status == "created"
    assert result.invariants_status == "created"
    assert result.invariant_count == 1
    assert result.litmus_directory_created is True
    assert "zero-config ASGI path detected" in result.support_summary
    assert result.config_path.read_text(encoding="utf-8") == "app: service.app:app\n"

    invariants = load_invariants(result.invariants_path)
    assert len(invariants) == 1
    assert invariants[0].request is not None
    assert invariants[0].request.path == "/payments/charge"


def test_bootstrap_repo_respects_existing_config_and_invariant_store(tmp_path) -> None:
    service_dir = tmp_path / "service"
    tests_dir = tmp_path / "tests"
    litmus_dir = tmp_path / ".litmus"
    service_dir.mkdir()
    tests_dir.mkdir()
    litmus_dir.mkdir()

    (tmp_path / "litmus.yaml").write_text("app: service.app:app\n", encoding="utf-8")
    existing_invariants_path = litmus_dir / "invariants.yaml"
    existing_invariants_path.write_text("[]\n", encoding="utf-8")

    (service_dir / "app.py").write_text("app = object()\n", encoding="utf-8")
    (tests_dir / "test_payments.py").write_text("", encoding="utf-8")

    result = bootstrap_repo(tmp_path)

    assert result.config_status == "existing"
    assert result.invariants_status == "existing"
    assert result.litmus_directory_created is False
    assert result.support_summary[0] == "explicit app config detected"
