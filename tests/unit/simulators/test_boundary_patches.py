from __future__ import annotations

from litmus.simulators.boundary_patches import _build_patched_orm_sessionmaker


def test_patched_orm_sessionmaker_preserves_keyword_bind_when_falling_back() -> None:
    captured: dict[str, object] = {}

    def original_sessionmaker(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "original-factory"

    bind = object()
    session_class = object()
    patched = _build_patched_orm_sessionmaker(original_sessionmaker)

    result = patched(bind=bind, class_=session_class, expire_on_commit=False)

    assert result == "original-factory"
    assert captured["args"] == ()
    assert captured["kwargs"] == {
        "bind": bind,
        "class_": session_class,
        "expire_on_commit": False,
    }
