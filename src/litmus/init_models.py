from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


BootstrapStatus = Literal["created", "existing"]


@dataclass(slots=True)
class InitBootstrapResult:
    app_reference: str
    config_path: Path
    invariants_path: Path
    config_status: BootstrapStatus
    invariants_status: BootstrapStatus
    invariant_count: int
    litmus_directory_created: bool
    support_summary: list[str]
