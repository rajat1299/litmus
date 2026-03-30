from __future__ import annotations

from litmus.dst.scheduler import DeterministicScheduler


def test_deterministic_scheduler_repeats_same_order_for_same_seed() -> None:
    scheduler_one = DeterministicScheduler(seed=7)
    scheduler_two = DeterministicScheduler(seed=7)
    runnable = ["http", "db", "redis", "email"]

    order_one = scheduler_one.order(runnable)
    order_two = scheduler_two.order(runnable)

    assert order_one == order_two
    assert sorted(order_one) == sorted(runnable)
