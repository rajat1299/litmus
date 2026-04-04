from __future__ import annotations

import json
from pathlib import Path
import subprocess
import textwrap

from litmus.runs import replay_record_for_seed


def test_litmus_verify_writes_replayable_run_record(tmp_path: Path) -> None:
    repo_root = _build_verify_repo(tmp_path)

    result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    latest_pointer = repo_root / ".litmus" / "runs" / "latest.json"
    latest_replayable_pointer = repo_root / ".litmus" / "runs" / "latest-replayable.json"
    assert latest_pointer.exists()
    assert latest_replayable_pointer.exists()

    latest_run_id = json.loads(latest_pointer.read_text(encoding="utf-8"))["run_id"]
    run_payload = json.loads((repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8"))

    assert run_payload["mode"] == "local"
    assert run_payload["status"] == "completed"
    assert run_payload["scope_label"] == "full repo"
    assert run_payload["activities"][0]["type"] == "verify"
    assert run_payload["activities"][0]["summary"]["scenarios"] == 1
    assert run_payload["activities"][0]["summary"]["invariants"] == {
        "total": 1,
        "confirmed": 1,
        "suggested": 0,
    }
    assert run_payload["artifacts"]["replay_traces"][0]["seed"] == "seed:1"
    transcript = run_payload["artifacts"]["replay_traces"][0]["execution_transcript"]
    assert transcript is not None
    assert transcript[-1] == {
        "kind": "response_completed",
        "status_code": 200,
    }
    assert run_payload["artifacts"]["replay_traces"][0]["target_selection"] == {
        "clean_path_targets": ["http"],
        "fault_path_targets": [],
        "selected_targets": ["http"],
        "probe_records": [
            {
                "phase": "clean_path",
                "trigger_target": None,
                "trigger_fault_kind": None,
                "discovered_targets": ["http"],
            },
            {
                "phase": "fault_path",
                "trigger_target": "http",
                "trigger_fault_kind": "timeout",
                "discovered_targets": ["http"],
            },
        ],
        "planned_fault_seed": {
            "seed_value": 1,
            "target": "http",
            "fault_kind": "timeout",
            "selection_source": "clean_path",
        },
    }
    assert not (repo_root / ".litmus" / "replay-traces.json").exists()


def test_litmus_replay_uses_run_store_even_without_legacy_trace_file_and_records_replay_run(tmp_path: Path) -> None:
    repo_root = _build_breaking_replay_repo(tmp_path)

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert verify_result.returncode == 1, verify_result.stdout

    latest_replayable_pointer = repo_root / ".litmus" / "runs" / "latest-replayable.json"
    source_run_id = json.loads(latest_replayable_pointer.read_text(encoding="utf-8"))["run_id"]
    (repo_root / ".litmus" / "replay-traces.json").unlink(missing_ok=True)

    replay_result = subprocess.run(
        ["litmus", "replay", "seed:1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert replay_result.returncode == 0, replay_result.stderr
    assert "Classification: breaking_change" in replay_result.stdout

    latest_run_id = json.loads((repo_root / ".litmus" / "runs" / "latest.json").read_text(encoding="utf-8"))["run_id"]
    replay_run_payload = json.loads(
        (repo_root / ".litmus" / "runs" / latest_run_id / "run.json").read_text(encoding="utf-8")
    )

    assert replay_run_payload["activities"][0]["type"] == "replay"
    assert replay_run_payload["activities"][0]["seed"] == "seed:1"
    assert replay_run_payload["activities"][0]["source_run_id"] == source_run_id
    assert json.loads(latest_replayable_pointer.read_text(encoding="utf-8"))["run_id"] == source_run_id


def test_exported_replay_record_lookup_uses_run_store_after_legacy_trace_file_is_deleted(tmp_path: Path) -> None:
    repo_root = _build_breaking_replay_repo(tmp_path)

    verify_result = subprocess.run(
        ["litmus", "verify"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert verify_result.returncode == 1, verify_result.stdout

    (repo_root / ".litmus" / "replay-traces.json").unlink(missing_ok=True)

    source_run, record = replay_record_for_seed(repo_root, "seed:1")

    assert source_run.run_id.startswith("run-")
    assert record.seed == "seed:1"
    assert record.path == "/health"


def _build_verify_repo(repo_root: Path) -> Path:
    service_dir = repo_root / "service"
    tests_dir = repo_root / "tests"
    service_dir.mkdir()
    tests_dir.mkdir()

    (service_dir / "app.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json


            class FastAPI:
                def __init__(self) -> None:
                    self.routes = {}

                def get(self, path: str):
                    def decorator(func):
                        self.routes[("GET", path)] = func
                        return func

                    return decorator

                async def __call__(self, scope, receive, send) -> None:
                    handler = self.routes[(scope["method"], scope["path"])]
                    response = await handler()
                    await send(
                        {
                            "type": "http.response.start",
                            "status": response["status_code"],
                            "headers": [(b"content-type", b"application/json")],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": json.dumps(response["json"]).encode("utf-8"),
                        }
                    )


            app = FastAPI()


            @app.get("/health")
            async def health():
                return {"status_code": 200, "json": {"status": "ok"}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (tests_dir / "test_health.py").write_text(
        textwrap.dedent(
            """
            def test_health_returns_200():
                request = {
                    "method": "GET",
                    "path": "/health",
                }
                response = {
                    "status_code": 200,
                    "json": {"status": "ok"},
                }

                assert response["status_code"] == 200
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return repo_root


def _build_breaking_replay_repo(repo_root: Path) -> Path:
    repo_root = _build_verify_repo(repo_root)
    app_path = repo_root / "service" / "app.py"
    app_path.write_text(
        app_path.read_text(encoding="utf-8").replace('"status_code": 200', '"status_code": 500').replace('"status": "ok"', '"status": "broken"'),
        encoding="utf-8",
    )
    return repo_root
