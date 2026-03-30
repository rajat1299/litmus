from __future__ import annotations

import asyncio

from litmus.simulators.sqlalchemy_async import (
    SimulatedAsyncEngine,
    TableSchema,
    UnsupportedDatabaseOperationError,
)


def test_simulated_async_engine_supports_crud_operations() -> None:
    engine = SimulatedAsyncEngine(
        schemas={
            "orders": TableSchema(primary_key="id", columns=("id", "status")),
        }
    )

    async def exercise() -> None:
        async with engine.session() as session:
            await session.insert("orders", {"id": "ord-1", "status": "pending"})
            assert await session.get("orders", "ord-1") == {"id": "ord-1", "status": "pending"}

            await session.update("orders", "ord-1", {"status": "paid"})
            assert await session.get("orders", "ord-1") == {"id": "ord-1", "status": "paid"}
            assert await session.all("orders") == [{"id": "ord-1", "status": "paid"}]

            await session.delete("orders", "ord-1")
            assert await session.get("orders", "ord-1") is None

    asyncio.run(exercise())


def test_simulated_async_engine_uses_read_committed_transactions() -> None:
    engine = SimulatedAsyncEngine(
        schemas={
            "orders": TableSchema(primary_key="id", columns=("id", "status")),
        }
    )

    async def exercise() -> None:
        async with engine.session() as writer:
            async with engine.session() as reader:
                await writer.begin()
                await writer.insert("orders", {"id": "ord-1", "status": "pending"})

                assert await writer.get("orders", "ord-1") == {"id": "ord-1", "status": "pending"}
                assert await reader.get("orders", "ord-1") is None

                await writer.commit()
                assert await reader.get("orders", "ord-1") == {"id": "ord-1", "status": "pending"}

                await writer.begin()
                await writer.update("orders", "ord-1", {"status": "failed"})
                assert await reader.get("orders", "ord-1") == {"id": "ord-1", "status": "pending"}

                await writer.rollback()
                assert await reader.get("orders", "ord-1") == {"id": "ord-1", "status": "pending"}

    asyncio.run(exercise())


def test_simulated_async_engine_reader_transaction_sees_newly_committed_rows() -> None:
    engine = SimulatedAsyncEngine(
        schemas={
            "orders": TableSchema(primary_key="id", columns=("id", "status")),
        }
    )

    async def exercise() -> None:
        async with engine.session() as writer:
            async with engine.session() as reader:
                await reader.begin()
                assert await reader.get("orders", "ord-1") is None

                await writer.begin()
                await writer.insert("orders", {"id": "ord-1", "status": "pending"})
                await writer.commit()

                assert await reader.get("orders", "ord-1") == {"id": "ord-1", "status": "pending"}

    asyncio.run(exercise())


def test_simulated_async_engine_fails_clearly_for_unsupported_operations() -> None:
    engine = SimulatedAsyncEngine(
        schemas={
            "orders": TableSchema(primary_key="id", columns=("id", "status")),
        }
    )

    async def exercise() -> None:
        async with engine.session() as session:
            try:
                await session.execute("SELECT * FROM orders")
            except UnsupportedDatabaseOperationError:
                return
            raise AssertionError("expected unsupported operation error")

    asyncio.run(exercise())
