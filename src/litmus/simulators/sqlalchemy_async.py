from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from litmus.dst.faults import FaultPlan


class DatabaseConnectionDroppedError(Exception):
    pass


class DatabasePoolExhaustedError(Exception):
    pass


class UnsupportedDatabaseOperationError(Exception):
    pass


@dataclass(slots=True, frozen=True)
class TableSchema:
    primary_key: str
    columns: tuple[str, ...] = ()


class SimulatedAsyncEngine:
    def __init__(
        self,
        schemas: dict[str, TableSchema],
        fault_plan: FaultPlan | None = None,
        pool_size: int = 5,
    ) -> None:
        self._schemas = schemas
        self._state: dict[str, dict[object, dict[str, object]]] = {
            table_name: {}
            for table_name in schemas
        }
        self._fault_plan = fault_plan or FaultPlan(seed=0)
        self._pool_size = pool_size
        self._active_sessions = 0
        self._step = 0

    def session(self) -> SimulatedAsyncSession:
        return SimulatedAsyncSession(engine=self)

    def _next_fault(self):
        self._step += 1
        return self._fault_plan.fault_for_step(self._step)


class SimulatedAsyncSession:
    def __init__(self, engine: SimulatedAsyncEngine) -> None:
        self._engine = engine
        self._closed = False
        self._dropped = False
        self._transaction_writes: dict[str, dict[object, dict[str, object]]] | None = None
        self._transaction_deletes: dict[str, set[object]] | None = None

    async def __aenter__(self) -> SimulatedAsyncSession:
        if self._engine._active_sessions >= self._engine._pool_size:
            raise DatabasePoolExhaustedError("simulated connection pool exhausted")
        self._engine._active_sessions += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if self._in_transaction():
            await self.rollback()
        self._engine._active_sessions = max(0, self._engine._active_sessions - 1)
        self._closed = True
        return False

    async def begin(self) -> None:
        self._ensure_open()
        self._apply_fault()
        self._transaction_writes = {
            table_name: {}
            for table_name in self._engine._schemas
        }
        self._transaction_deletes = {
            table_name: set()
            for table_name in self._engine._schemas
        }

    async def commit(self) -> None:
        self._ensure_open()
        self._apply_fault()
        if not self._in_transaction():
            return
        assert self._transaction_writes is not None
        assert self._transaction_deletes is not None

        for table_name, deleted_primary_keys in self._transaction_deletes.items():
            for primary_key in deleted_primary_keys:
                self._engine._state[table_name].pop(primary_key, None)

        for table_name, staged_rows in self._transaction_writes.items():
            for primary_key, row in staged_rows.items():
                self._engine._state[table_name][primary_key] = deepcopy(row)

        self._clear_transaction()

    async def rollback(self) -> None:
        self._ensure_open(allow_dropped=True)
        self._clear_transaction()

    async def insert(self, table_name: str, row: dict[str, object]) -> None:
        schema = self._schema(table_name)
        self._apply_fault()
        primary_key = row[schema.primary_key]
        if self._in_transaction():
            assert self._transaction_writes is not None
            assert self._transaction_deletes is not None
            self._transaction_deletes[table_name].discard(primary_key)
            self._transaction_writes[table_name][primary_key] = deepcopy(row)
            return
        self._engine._state[table_name][primary_key] = deepcopy(row)

    async def get(self, table_name: str, primary_key: object) -> dict[str, object] | None:
        self._schema(table_name)
        self._apply_fault()
        row = self._current_row(table_name, primary_key)
        return deepcopy(row) if row is not None else None

    async def all(self, table_name: str) -> list[dict[str, object]]:
        self._schema(table_name)
        self._apply_fault()
        table_rows = {
            primary_key: deepcopy(row)
            for primary_key, row in self._engine._state[table_name].items()
        }
        if self._in_transaction():
            assert self._transaction_writes is not None
            assert self._transaction_deletes is not None
            for primary_key in self._transaction_deletes[table_name]:
                table_rows.pop(primary_key, None)
            for primary_key, row in self._transaction_writes[table_name].items():
                table_rows[primary_key] = deepcopy(row)
        return [
            deepcopy(table_rows[primary_key])
            for primary_key in sorted(table_rows, key=str)
        ]

    async def update(self, table_name: str, primary_key: object, values: dict[str, object]) -> None:
        schema = self._schema(table_name)
        self._apply_fault()
        current_row = self._current_row(table_name, primary_key)
        if current_row is None:
            raise KeyError(f"no simulated row for {table_name}.{schema.primary_key}={primary_key!r}")
        current_row.update(values)
        if self._in_transaction():
            assert self._transaction_writes is not None
            assert self._transaction_deletes is not None
            self._transaction_deletes[table_name].discard(primary_key)
            self._transaction_writes[table_name][primary_key] = current_row
            return
        self._engine._state[table_name][primary_key] = current_row

    async def delete(self, table_name: str, primary_key: object) -> None:
        schema = self._schema(table_name)
        self._apply_fault()
        if self._current_row(table_name, primary_key) is None:
            raise KeyError(f"no simulated row for {table_name}.{schema.primary_key}={primary_key!r}")
        if self._in_transaction():
            assert self._transaction_writes is not None
            assert self._transaction_deletes is not None
            self._transaction_writes[table_name].pop(primary_key, None)
            self._transaction_deletes[table_name].add(primary_key)
            return
        del self._engine._state[table_name][primary_key]

    async def execute(self, statement: str) -> None:
        self._ensure_open()
        raise UnsupportedDatabaseOperationError(
            f"raw simulated SQLAlchemy execution is not supported: {statement}"
        )

    def _schema(self, table_name: str) -> TableSchema:
        self._ensure_open()
        if table_name not in self._engine._schemas:
            raise KeyError(f"unknown simulated table: {table_name}")
        return self._engine._schemas[table_name]

    def _current_row(self, table_name: str, primary_key: object) -> dict[str, object] | None:
        if self._in_transaction():
            assert self._transaction_writes is not None
            assert self._transaction_deletes is not None
            if primary_key in self._transaction_deletes[table_name]:
                return None
            if primary_key in self._transaction_writes[table_name]:
                return deepcopy(self._transaction_writes[table_name][primary_key])
        row = self._engine._state[table_name].get(primary_key)
        return deepcopy(row) if row is not None else None

    def _in_transaction(self) -> bool:
        return self._transaction_writes is not None and self._transaction_deletes is not None

    def _clear_transaction(self) -> None:
        self._transaction_writes = None
        self._transaction_deletes = None

    def _ensure_open(self, allow_dropped: bool = False) -> None:
        if self._closed:
            raise RuntimeError("simulated session is closed")
        if self._dropped and not allow_dropped:
            raise DatabaseConnectionDroppedError("simulated connection already dropped")

    def _apply_fault(self) -> None:
        fault = self._engine._next_fault()
        if fault is None or fault.target not in {"sqlalchemy", "database", "db"}:
            return
        if fault.kind == "connection_dropped":
            self._clear_transaction()
            self._dropped = True
            raise DatabaseConnectionDroppedError("simulated database connection dropped")
        if fault.kind == "pool_exhausted":
            raise DatabasePoolExhaustedError("simulated connection pool exhausted")
