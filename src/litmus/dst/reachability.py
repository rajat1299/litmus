from __future__ import annotations

from dataclasses import dataclass, field


TARGET_AWARE_COVERAGE_FAULTS: dict[str, str] = {
    "http": "timeout",
    "redis": "timeout",
    "sqlalchemy": "connection_dropped",
}


@dataclass(slots=True, frozen=True)
class ReachabilityProbeRecord:
    phase: str
    trigger_target: str | None = None
    trigger_fault_kind: str | None = None
    discovered_targets: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "trigger_target": self.trigger_target,
            "trigger_fault_kind": self.trigger_fault_kind,
            "discovered_targets": list(self.discovered_targets),
        }


@dataclass(slots=True, frozen=True)
class ScenarioReachability:
    clean_path_targets: tuple[str, ...] = ()
    fault_path_targets: tuple[str, ...] = ()
    selected_targets: tuple[str, ...] = ()
    probe_records: tuple[ReachabilityProbeRecord, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "clean_path_targets": list(self.clean_path_targets),
            "fault_path_targets": list(self.fault_path_targets),
            "selected_targets": list(self.selected_targets),
            "probe_records": [record.to_dict() for record in self.probe_records],
        }


@dataclass(slots=True, frozen=True)
class PlannedFaultSeed:
    seed_value: int
    target: str
    fault_kind: str
    selection_source: str = "clean_path"

    def to_dict(self) -> dict[str, object]:
        return {
            "seed_value": self.seed_value,
            "target": self.target,
            "fault_kind": self.fault_kind,
            "selection_source": self.selection_source,
        }


def plan_local_fault_seeds(
    *,
    seed_start: int,
    reachability: ScenarioReachability,
    seeds_per_scenario: int,
) -> list[PlannedFaultSeed]:
    if seeds_per_scenario <= 0 or not reachability.selected_targets:
        return []

    planned: list[PlannedFaultSeed] = []
    clean_targets = set(reachability.clean_path_targets)
    targets = list(reachability.selected_targets)

    for offset in range(seeds_per_scenario):
        target = targets[offset % len(targets)]
        planned.append(
            PlannedFaultSeed(
                seed_value=seed_start + offset,
                target=target,
                fault_kind=representative_fault_kind_for_target(target),
                selection_source="clean_path" if target in clean_targets else "fault_path",
            )
        )

    return planned


def representative_fault_kind_for_target(target: str) -> str:
    return TARGET_AWARE_COVERAGE_FAULTS.get(target, "timeout")
