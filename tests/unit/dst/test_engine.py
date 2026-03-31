from __future__ import annotations

from pathlib import Path

from litmus.dst.engine import run_verification


def test_run_verification_uses_ci_property_budget(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    async def fake_run_replay(_app, _app_reference, _scenarios):
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)
    captured: dict[str, int] = {}

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path, mode="ci")

    assert captured["max_examples"] == 500


def test_run_verification_defaults_to_local_property_budget(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("litmus.dst.engine.discover_app_reference", lambda _root: "service.app:app")
    monkeypatch.setattr("litmus.dst.engine.load_asgi_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("litmus.dst.engine._collect_routes", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine._collect_test_files", lambda _root: [])
    monkeypatch.setattr("litmus.dst.engine.mine_invariants_from_tests", lambda _files: [])
    monkeypatch.setattr("litmus.dst.engine.build_scenarios", lambda _routes, _invariants: [])

    async def fake_run_replay(_app, _app_reference, _scenarios):
        return [], []

    monkeypatch.setattr("litmus.dst.engine._run_replay", fake_run_replay)
    captured: dict[str, int] = {}

    def fake_run_property_checks(_app, _invariants, *, max_examples: int):
        captured["max_examples"] = max_examples
        return []

    monkeypatch.setattr("litmus.dst.engine._run_property_checks", fake_run_property_checks)

    run_verification(tmp_path)

    assert captured["max_examples"] == 100
