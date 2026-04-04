from __future__ import annotations

import asyncio

from litmus.dst.faults import FaultPlan, FaultSpec
from litmus.simulators.redis_async import (
    SimulatedRedis,
    UnsupportedRedisOperationError,
)


def test_simulated_redis_supports_strings_hashes_and_lists() -> None:
    redis = SimulatedRedis()

    async def exercise() -> None:
        assert await redis.get("missing") is None

        assert await redis.set("status", "ok") is True
        assert await redis.get("status") == "ok"

        assert await redis.incr("counter") == 1
        assert await redis.incr("counter") == 2
        assert await redis.get("counter") == 2

        assert await redis.hset("order:1", "status", "pending") == 1
        assert await redis.hset("order:1", "status", "paid") == 0
        assert await redis.hset("order:1", "amount", 42) == 1
        assert await redis.hget("order:1", "status") == "paid"
        assert await redis.hgetall("order:1") == {"status": "paid", "amount": 42}

        assert await redis.rpush("queue", "job-1", "job-2") == 2
        assert await redis.lpush("queue", "job-0") == 3
        assert await redis.lpop("queue") == "job-0"
        assert await redis.brpop("queue", timeout=1) == ("queue", "job-2")
        assert await redis.lpop("queue") == "job-1"

        assert await redis.delete("status", "counter", "missing") == 2

    asyncio.run(exercise())


def test_simulated_redis_expires_keys_and_times_out_blocking_pops_deterministically() -> None:
    redis = SimulatedRedis()

    async def exercise() -> None:
        assert await redis.setex("session", 5, "alive") is True
        assert await redis.get("session") == "alive"

        await redis.advance_time(4)
        assert await redis.get("session") == "alive"

        await redis.advance_time(1)
        assert await redis.get("session") is None

        waiter = asyncio.create_task(redis.brpop("jobs", timeout=5))
        await asyncio.sleep(0)

        await redis.advance_time(4)
        assert waiter.done() is False

        await redis.advance_time(1)
        assert await waiter is None

    asyncio.run(exercise())


def test_simulated_redis_rejects_unsupported_pubsub_operations() -> None:
    redis = SimulatedRedis()

    async def exercise() -> None:
        try:
            await redis.publish("events", "payload")
        except UnsupportedRedisOperationError:
            return
        raise AssertionError("expected unsupported redis operation error")

    asyncio.run(exercise())


def test_partial_write_fault_is_not_recorded_for_non_partial_write_operations() -> None:
    events: list[tuple[str, dict[str, object]]] = []
    redis = SimulatedRedis(
        fault_plan=FaultPlan(
            seed=13,
            schedule={
                1: FaultSpec(kind="partial_write", target="redis"),
            },
        ),
        record_event=lambda kind, **metadata: events.append((kind, metadata)),
    )

    async def exercise() -> None:
        assert await redis.get("status") is None

    asyncio.run(exercise())

    assert events == []
