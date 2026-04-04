from __future__ import annotations

from pathlib import Path

import pytest

from litmus.discovery.app import AppLoadError, AppLoader, discover_app_reference, load_asgi_app


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


def test_app_loader_reloads_conflicting_helper_modules_across_repo_roots(tmp_path: Path) -> None:
    repo_one = tmp_path / "repo-one"
    repo_two = tmp_path / "repo-two"
    _write_loader_repo(repo_one, status="one")
    _write_loader_repo(repo_two, status="two")

    loader = AppLoader()

    first_app = loader.load("service.main:app", repo_one)
    second_app = loader.load("service.main:app", repo_two)

    assert first_app.status == "one"
    assert second_app.status == "two"


@pytest.mark.parametrize(
    ("reference", "expected_message"),
    [
        ("service.main", "Expected '<module>:<attribute>'"),
        ("missing.module:app", "Could not import module"),
        ("service.main:missing_app", "Missing attribute"),
    ],
)
def test_app_loader_wraps_reference_failures_in_app_load_error(
    tmp_path: Path,
    reference: str,
    expected_message: str,
) -> None:
    service = tmp_path / "service"
    service.mkdir()
    (service / "main.py").write_text("app = object()\n", encoding="utf-8")

    loader = AppLoader()

    with pytest.raises(AppLoadError) as exc_info:
        loader.load(reference, tmp_path)

    message = str(exc_info.value)
    assert reference in message
    assert expected_message in message


def test_load_asgi_app_does_not_replace_unsupported_type_imports_in_user_module(tmp_path: Path) -> None:
    sqlalchemy_ext = tmp_path / "sqlalchemy" / "ext"
    redis_dir = tmp_path / "redis"
    service = tmp_path / "service"
    sqlalchemy_ext.mkdir(parents=True)
    redis_dir.mkdir()
    service.mkdir()

    (tmp_path / "sqlalchemy" / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext / "__init__.py").write_text("", encoding="utf-8")
    (sqlalchemy_ext / "asyncio.py").write_text(
        """
class AsyncSession:
    pass

def create_async_engine(*args, **kwargs):
    return object()

def async_sessionmaker(*args, **kwargs):
    return object()
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (redis_dir / "__init__.py").write_text("", encoding="utf-8")
    (redis_dir / "asyncio.py").write_text(
        """
class Redis:
    pass

class RedisCluster:
    pass

def from_url(*args, **kwargs):
    return object()
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (service / "__init__.py").write_text("", encoding="utf-8")
    (service / "main.py").write_text(
        """
from redis.asyncio import RedisCluster
from sqlalchemy.ext.asyncio import AsyncSession


class FastAPI:
    pass


session_type = AsyncSession
cluster_type = RedisCluster
app = FastAPI()
""".strip()
        + "\n",
        encoding="utf-8",
    )

    load_asgi_app("service.main:app", tmp_path)

    import service.main as main_module

    assert isinstance(main_module.session_type, type)
    assert main_module.session_type.__name__ == "AsyncSession"
    assert isinstance(main_module.cluster_type, type)
    assert main_module.cluster_type.__name__ == "RedisCluster"


def _write_loader_repo(root: Path, *, status: str) -> None:
    service = root / "service"
    service.mkdir(parents=True)
    (root / "shared.py").write_text(f'STATUS = "{status}"\n', encoding="utf-8")
    (service / "main.py").write_text(
        """
from shared import STATUS


class FastAPI:
    def __init__(self, status: str) -> None:
        self.status = status


app = FastAPI(STATUS)
""".strip()
        + "\n",
        encoding="utf-8",
    )
