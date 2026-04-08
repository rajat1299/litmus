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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ReachabilityProbeRecord:
        return cls(
            phase=str(payload["phase"]),
            trigger_target=None if payload.get("trigger_target") is None else str(payload["trigger_target"]),
            trigger_fault_kind=None
            if payload.get("trigger_fault_kind") is None
            else str(payload["trigger_fault_kind"]),
            discovered_targets=tuple(str(target) for target in payload.get("discovered_targets", [])),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ScenarioReachability:
        return cls(
            clean_path_targets=tuple(str(target) for target in payload.get("clean_path_targets", [])),
            fault_path_targets=tuple(str(target) for target in payload.get("fault_path_targets", [])),
            selected_targets=tuple(str(target) for target in payload.get("selected_targets", [])),
            probe_records=tuple(
                ReachabilityProbeRecord.from_dict(record)
                for record in payload.get("probe_records", [])
            ),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> PlannedFaultSeed:
        return cls(
            seed_value=int(payload["seed_value"]),
            target=str(payload["target"]),
            fault_kind=str(payload["fault_kind"]),
            selection_source=str(payload.get("selection_source", "clean_path")),
        )


@dataclass(slots=True, frozen=True)
class TargetSelectionArtifact:
    reachability: ScenarioReachability
    planned_fault_seed: PlannedFaultSeed

    def to_dict(self) -> dict[str, object]:
        payload = self.reachability.to_dict()
        payload["planned_fault_seed"] = self.planned_fault_seed.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> TargetSelectionArtifact:
        reachability_payload = dict(payload)
        planned_fault_seed_payload = reachability_payload.pop("planned_fault_seed")
        return cls(
            reachability=ScenarioReachability.from_dict(reachability_payload),
            planned_fault_seed=PlannedFaultSeed.from_dict(planned_fault_seed_payload),
        )

    @classmethod
    def from_reachability(
        cls,
        *,
        reachability: ScenarioReachability,
        planned_fault_seed: PlannedFaultSeed,
    ) -> TargetSelectionArtifact:
        return cls(
            reachability=reachability,
            planned_fault_seed=planned_fault_seed,
        )


def plan_local_fault_seeds(
    *,
    seed_start: int,
    reachability: ScenarioReachability,
    seeds_per_scenario: int,
) -> list[PlannedFaultSeed]:
    if seeds_per_scenario <= 0 or not reachability.selected_targets:
        return []

    return [
        planned_fault_seed_for_value(
            seed_start=seed_start,
            seed_value=seed_start + offset,
            reachability=reachability,
        )
        for offset in range(seeds_per_scenario)
    ]


def planned_fault_seed_for_value(
    *,
    seed_start: int,
    seed_value: int,
    reachability: ScenarioReachability,
) -> PlannedFaultSeed:
    if not reachability.selected_targets:
        raise ValueError("Cannot select a planned fault seed without any selected targets.")

    offset = max(seed_value - seed_start, 0)
    clean_targets = set(reachability.clean_path_targets)
    targets = list(reachability.selected_targets)
    target = targets[offset % len(targets)]
    return PlannedFaultSeed(
        seed_value=seed_value,
        target=target,
        fault_kind=representative_fault_kind_for_target(target),
        selection_source="clean_path" if target in clean_targets else "fault_path",
    )


def representative_fault_kind_for_target(target: str) -> str:
    return TARGET_AWARE_COVERAGE_FAULTS.get(target, "timeout")
