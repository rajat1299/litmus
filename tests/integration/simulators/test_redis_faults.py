from __future__ import annotations

import asyncio

from litmus.dst.faults import FaultPlan, FaultSpec
from litmus.simulators.redis_async import (
    RedisConnectionRefusedError,
    RedisMovedError,
    RedisPartialWriteError,
    RedisTimeoutError,
    SimulatedRedis,
)


def test_simulated_redis_raises_connection_refused_fault() -> None:
    redis = SimulatedRedis(
        fault_plan=FaultPlan(
            seed=21,
            schedule={
                1: FaultSpec(kind="connection_refused", target="redis"),
            },
        )
    )

    async def exercise() -> None:
        try:
            await redis.get("status")
        except RedisConnectionRefusedError:
            return
        raise AssertionError("expected redis connection refusal")

    asyncio.run(exercise())


def test_simulated_redis_raises_timeout_fault_for_blocking_pop() -> None:
    redis = SimulatedRedis(
        fault_plan=FaultPlan(
            seed=22,
            schedule={
                1: FaultSpec(kind="timeout", target="redis"),
            },
        )
    )

    async def exercise() -> None:
        try:
            await redis.brpop("jobs", timeout=5)
        except RedisTimeoutError:
            return
        raise AssertionError("expected redis timeout")

    asyncio.run(exercise())


def test_simulated_redis_applies_partial_write_fault_to_multi_value_push() -> None:
    redis = SimulatedRedis(
        fault_plan=FaultPlan(
            seed=23,
            schedule={
                1: FaultSpec(
                    kind="partial_write",
                    target="redis",
                    params={"applied_count": 1},
                ),
            },
        )
    )

    async def exercise() -> None:
        try:
            await redis.rpush("jobs", "job-1", "job-2")
        except RedisPartialWriteError:
            pass
        else:
            raise AssertionError("expected redis partial write")

        assert await redis.lpop("jobs") == "job-1"
        assert await redis.lpop("jobs") is None

    asyncio.run(exercise())


def test_simulated_redis_raises_moved_fault_with_slot_and_location() -> None:
    redis = SimulatedRedis(
        fault_plan=FaultPlan(
            seed=24,
            schedule={
                1: FaultSpec(
                    kind="moved",
                    target="redis",
                    params={"slot": 42, "location": "127.0.0.1:7001"},
                ),
            },
        )
    )

    async def exercise() -> None:
        try:
            await redis.get("status")
        except RedisMovedError as exc:
            assert exc.slot == 42
            assert exc.location == "127.0.0.1:7001"
            return
        raise AssertionError("expected redis MOVED error")

    asyncio.run(exercise())
