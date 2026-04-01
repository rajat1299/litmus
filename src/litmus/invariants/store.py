from __future__ import annotations

from pathlib import Path

import yaml

from litmus.invariants.models import Invariant


def default_invariants_path(root: Path | str) -> Path:
    return Path(root) / ".litmus" / "invariants.yaml"


def save_invariants(path: Path | str, invariants: list[Invariant]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = [invariant.model_dump(mode="json", by_alias=True, exclude_none=True) for invariant in invariants]
    output_path.write_text(yaml.safe_dump(serialized, sort_keys=False), encoding="utf-8")


def load_invariants(path: Path | str) -> list[Invariant]:
    input_path = Path(path)
    data = yaml.safe_load(input_path.read_text(encoding="utf-8")) or []
    return [Invariant.model_validate(item) for item in data]
