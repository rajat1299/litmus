from __future__ import annotations

from litmus.dst.reachability import (
    PlannedFaultSeed,
    ReachabilityProbeRecord,
    ScenarioReachability,
    TargetSelectionArtifact,
    planned_fault_seed_for_value,
    plan_local_fault_seeds,
)


def test_scenario_reachability_serializes_clean_and_fault_path_targets() -> None:
    reachability = ScenarioReachability(
        clean_path_targets=("http",),
        fault_path_targets=("redis",),
        selected_targets=("http", "redis"),
        probe_records=(
            ReachabilityProbeRecord(
                phase="clean_path",
                trigger_target=None,
                trigger_fault_kind=None,
                discovered_targets=("http",),
            ),
            ReachabilityProbeRecord(
                phase="fault_path",
                trigger_target="http",
                trigger_fault_kind="timeout",
                discovered_targets=("http", "redis"),
            ),
        ),
    )

    assert reachability.to_dict() == {
        "clean_path_targets": ["http"],
        "fault_path_targets": ["redis"],
        "selected_targets": ["http", "redis"],
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
                "discovered_targets": ["http", "redis"],
            },
        ],
    }


def test_plan_local_fault_seeds_covers_each_target_before_repeating() -> None:
    reachability = ScenarioReachability(
        clean_path_targets=("http",),
        fault_path_targets=("redis",),
        selected_targets=("http", "redis"),
    )

    planned = plan_local_fault_seeds(seed_start=1, reachability=reachability, seeds_per_scenario=3)

    assert planned == [
        PlannedFaultSeed(seed_value=1, target="http", fault_kind="timeout"),
        PlannedFaultSeed(seed_value=2, target="redis", fault_kind="timeout", selection_source="fault_path"),
        PlannedFaultSeed(seed_value=3, target="http", fault_kind="connection_refused"),
    ]


def test_plan_local_fault_seeds_diversifies_fault_kinds_for_single_target_budget() -> None:
    reachability = ScenarioReachability(
        clean_path_targets=("http",),
        fault_path_targets=(),
        selected_targets=("http",),
    )

    planned = plan_local_fault_seeds(seed_start=1, reachability=reachability, seeds_per_scenario=3)

    assert [(seed.target, seed.fault_kind) for seed in planned] == [
        ("http", "timeout"),
        ("http", "connection_refused"),
        ("http", "http_error"),
    ]


def test_plan_local_fault_seeds_uses_target_aware_representative_faults() -> None:
    reachability = ScenarioReachability(
        clean_path_targets=("http",),
        fault_path_targets=("sqlalchemy", "redis"),
        selected_targets=("http", "sqlalchemy", "redis"),
    )

    planned = plan_local_fault_seeds(seed_start=4, reachability=reachability, seeds_per_scenario=3)

    assert [(seed.target, seed.fault_kind) for seed in planned] == [
        ("http", "timeout"),
        ("sqlalchemy", "connection_dropped"),
        ("redis", "timeout"),
    ]


def test_planned_fault_seed_for_value_uses_absolute_seed_position_within_scenario_window() -> None:
    reachability = ScenarioReachability(
        clean_path_targets=("http",),
        fault_path_targets=("sqlalchemy", "redis"),
        selected_targets=("http", "sqlalchemy", "redis"),
    )

    planned = planned_fault_seed_for_value(
        seed_start=1,
        seed_value=2,
        reachability=reachability,
    )

    assert planned == PlannedFaultSeed(
        seed_value=2,
        target="sqlalchemy",
        fault_kind="connection_dropped",
        selection_source="fault_path",
    )


def test_target_selection_artifact_captures_reachability_and_planned_seed() -> None:
    reachability = ScenarioReachability(
        clean_path_targets=("http",),
        fault_path_targets=("redis",),
        selected_targets=("http", "redis"),
        probe_records=(
            ReachabilityProbeRecord(
                phase="clean_path",
                discovered_targets=("http",),
            ),
        ),
    )

    artifact = TargetSelectionArtifact.from_reachability(
        reachability=reachability,
        planned_fault_seed=PlannedFaultSeed(
            seed_value=2,
            target="redis",
            fault_kind="timeout",
            selection_source="fault_path",
        ),
    )

    assert artifact.to_dict() == {
        "clean_path_targets": ["http"],
        "fault_path_targets": ["redis"],
        "selected_targets": ["http", "redis"],
        "probe_records": [
            {
                "phase": "clean_path",
                "trigger_target": None,
                "trigger_fault_kind": None,
                "discovered_targets": ["http"],
            }
        ],
        "planned_fault_seed": {
            "seed_value": 2,
            "target": "redis",
            "fault_kind": "timeout",
            "selection_source": "fault_path",
        },
    }
