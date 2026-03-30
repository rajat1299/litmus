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
