from __future__ import annotations

from pathlib import Path

from litmus.discovery.app import discover_app_reference, load_asgi_app


def test_discover_app_reference_prefers_explicit_config(tmp_path: Path) -> None:
    (tmp_path / "litmus.yaml").write_text('app: "service.api:app"\n', encoding="utf-8")
    (tmp_path / "main.py").write_text("app = object()\n", encoding="utf-8")

    assert discover_app_reference(tmp_path) == "service.api:app"


def test_discover_app_reference_finds_fastapi_app_fixture() -> None:
    fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "apps" / "simple_fastapi_app"

    assert discover_app_reference(fixture_root) == "main:app"


def test_discover_app_reference_finds_starlette_app(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        """
class Starlette:
    pass

app = Starlette()
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert discover_app_reference(tmp_path) == "main:app"


def test_load_asgi_app_imports_reference(monkeypatch) -> None:
    fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "apps" / "simple_fastapi_app"
    monkeypatch.syspath_prepend(str(fixture_root))

    app = load_asgi_app("main:app")

    assert app.__class__.__name__ == "FastAPI"


def test_load_asgi_app_imports_discovered_reference_from_repo_root(tmp_path: Path) -> None:
    service = tmp_path / "service"
    service.mkdir()
    (service / "main.py").write_text(
        """
class FastAPI:
    pass

app = FastAPI()
""".strip()
        + "\n",
        encoding="utf-8",
    )

    reference = discover_app_reference(tmp_path)

    app = load_asgi_app(reference, tmp_path)

    assert app.__class__.__name__ == "FastAPI"


def test_load_asgi_app_observes_on_disk_app_edits_across_repeated_loads(tmp_path: Path) -> None:
    service = tmp_path / "service"
    service.mkdir()
    app_path = service / "main.py"
    app_path.write_text(
        """
class FastAPI:
    def __init__(self, status: str) -> None:
        self.status = status

app = FastAPI("ok")
""".strip()
        + "\n",
        encoding="utf-8",
    )

    first_app = load_asgi_app("service.main:app", tmp_path)
    assert first_app.status == "ok"

    app_path.write_text(
        """
class FastAPI:
    def __init__(self, status: str) -> None:
        self.status = status

app = FastAPI("broken")
""".strip()
        + "\n",
        encoding="utf-8",
    )

    second_app = load_asgi_app("service.main:app", tmp_path)
    assert second_app.status == "broken"
