from __future__ import annotations

from litmus.dst.faults import build_fault_plan


def test_build_fault_plan_is_deterministic_and_lookup_works() -> None:
    plan_one = build_fault_plan(
        seed=11,
        steps=5,
        targets=["http", "db"],
        kinds=["timeout", "slow_response"],
    )
    plan_two = build_fault_plan(
        seed=11,
        steps=5,
        targets=["http", "db"],
        kinds=["timeout", "slow_response"],
    )

    assert plan_one == plan_two
    assert plan_one.fault_for_step(99) is None

    populated_steps = sorted(plan_one.schedule)
    assert populated_steps
    assert plan_one.fault_for_step(populated_steps[0]) == plan_two.fault_for_step(populated_steps[0])

