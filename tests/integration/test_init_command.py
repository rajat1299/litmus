from __future__ import annotations

import subprocess
import textwrap


def test_litmus_init_bootstraps_repo_and_prints_summary(tmp_path) -> None:
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

    result = subprocess.run(
        ["litmus", "init"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Litmus init" in result.stdout
    assert "App: service.app:app" in result.stdout
    assert "Config: created litmus.yaml" in result.stdout
    assert "Invariants: created .litmus/invariants.yaml (1 mined)" in result.stdout
    assert "Support: zero-config ASGI path detected" in result.stdout


def test_litmus_init_repairs_existing_config_without_app_reference(tmp_path) -> None:
    service_dir = tmp_path / "service"
    tests_dir = tmp_path / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (tmp_path / "litmus.yaml").write_text("{}\n", encoding="utf-8")
    (service_dir / "main.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations


            class FastAPI:
                pass


            app = FastAPI()
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["litmus", "init"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "App: service.main:app" in result.stdout
    assert "Config: updated litmus.yaml" in result.stdout
    assert (tmp_path / "litmus.yaml").read_text(encoding="utf-8") == "app: service.main:app\n"
