from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from litmus.config import FaultProfile, load_repo_config
from litmus.invariants.store import load_invariants


def test_litmus_invariants_list_shows_curated_invariants(tmp_path: Path) -> None:
    _write_invariants_fixture(tmp_path)

    result = subprocess.run(
        ["litmus", "invariants", "list"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Litmus invariants" in result.stdout
    assert "Count: 2" in result.stdout
    assert "charge_returns_200_on_success [confirmed]" in result.stdout
    assert "charge_is_idempotent_on_retry [suggested]" in result.stdout


def test_litmus_invariants_show_prints_named_invariant_details(tmp_path: Path) -> None:
    _write_invariants_fixture(tmp_path)

    result = subprocess.run(
        ["litmus", "invariants", "show", "charge_is_idempotent_on_retry"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Name: charge_is_idempotent_on_retry" in result.stdout
    assert "Status: suggested" in result.stdout
    assert "Type: property" in result.stdout
    assert "Source: llm:diff_analysis" in result.stdout


def test_litmus_invariants_set_status_updates_curated_invariant_file(tmp_path: Path) -> None:
    invariants_path = _write_invariants_fixture(tmp_path)

    result = subprocess.run(
        [
            "litmus",
            "invariants",
            "set-status",
            "charge_is_idempotent_on_retry",
            "--confirmed",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Updated invariant charge_is_idempotent_on_retry to confirmed." in result.stdout

    invariants = load_invariants(invariants_path)
    assert invariants[1].status.value == "confirmed"


def test_litmus_config_set_writes_explicit_litmus_yaml_values(tmp_path: Path) -> None:
    app_result = subprocess.run(
        ["litmus", "config", "set", "app", "service.main:app"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    suggested_result = subprocess.run(
        ["litmus", "config", "set", "suggested_invariants", "true"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    fault_profile_result = subprocess.run(
        ["litmus", "config", "set", "fault_profile", "hostile"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert app_result.returncode == 0, app_result.stderr
    assert suggested_result.returncode == 0, suggested_result.stderr
    assert fault_profile_result.returncode == 0, fault_profile_result.stderr
    assert "Set app = service.main:app" in app_result.stdout
    assert "Set suggested_invariants = true" in suggested_result.stdout
    assert "Set fault_profile = hostile" in fault_profile_result.stdout

    config = load_repo_config(tmp_path)
    assert config.app == "service.main:app"
    assert config.suggested_invariants is True
    assert config.fault_profile is FaultProfile.HOSTILE

    config_text = (tmp_path / "litmus.yaml").read_text(encoding="utf-8")
    assert "app: service.main:app" in config_text
    assert "suggested_invariants: true" in config_text
    assert "fault_profile: hostile" in config_text


def _write_invariants_fixture(tmp_path: Path) -> Path:
    invariants_path = tmp_path / ".litmus" / "invariants.yaml"
    invariants_path.parent.mkdir(parents=True, exist_ok=True)
    invariants_path.write_text(
        textwrap.dedent(
            """
            - name: charge_returns_200_on_success
              source: mined:test_payments.py::test_charge_returns_200_on_success
              status: confirmed
              type: differential
              request:
                method: POST
                path: /payments/charge
              response:
                status_code: 200
                json:
                  status: charged
            - name: charge_is_idempotent_on_retry
              source: llm:diff_analysis
              status: suggested
              type: property
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return invariants_path
