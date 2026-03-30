from __future__ import annotations

import asyncio

from litmus.dst.faults import FaultPlan, FaultSpec
from litmus.simulators.sqlalchemy_async import (
    DatabaseConnectionDroppedError,
    DatabasePoolExhaustedError,
    SimulatedAsyncEngine,
    TableSchema,
)


def test_simulated_async_engine_rolls_back_transaction_on_connection_drop() -> None:
    engine = SimulatedAsyncEngine(
        schemas={
            "orders": TableSchema(primary_key="id", columns=("id", "status")),
        },
        fault_plan=FaultPlan(
            seed=17,
            schedule={
                2: FaultSpec(kind="connection_dropped", target="sqlalchemy"),
            },
        ),
    )

    async def exercise() -> None:
        async with engine.session() as session:
            await session.begin()
            try:
                await session.insert("orders", {"id": "ord-1", "status": "pending"})
            except DatabaseConnectionDroppedError:
                pass
            else:
                raise AssertionError("expected connection drop fault")

        async with engine.session() as session:
            assert await session.get("orders", "ord-1") is None

    asyncio.run(exercise())


def test_simulated_async_engine_enforces_pool_limits() -> None:
    engine = SimulatedAsyncEngine(
        schemas={
            "orders": TableSchema(primary_key="id", columns=("id", "status")),
        },
        pool_size=1,
    )

    async def exercise() -> None:
        first = engine.session()
        await first.__aenter__()

        try:
            second = engine.session()
            try:
                await second.__aenter__()
            except DatabasePoolExhaustedError:
                return
            raise AssertionError("expected pool exhaustion")
        finally:
            await first.__aexit__(None, None, None)

    asyncio.run(exercise())
