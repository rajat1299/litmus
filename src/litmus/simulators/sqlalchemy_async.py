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

    def _copy_state(self) -> dict[str, dict[object, dict[str, object]]]:
        return {
            table_name: {
                primary_key: deepcopy(row)
                for primary_key, row in table_rows.items()
            }
            for table_name, table_rows in self._state.items()
        }

    def _next_fault(self):
        self._step += 1
        return self._fault_plan.fault_for_step(self._step)


class SimulatedAsyncSession:
    def __init__(self, engine: SimulatedAsyncEngine) -> None:
        self._engine = engine
        self._closed = False
        self._dropped = False
        self._transaction_state: dict[str, dict[object, dict[str, object]]] | None = None

    async def __aenter__(self) -> SimulatedAsyncSession:
        if self._engine._active_sessions >= self._engine._pool_size:
            raise DatabasePoolExhaustedError("simulated connection pool exhausted")
        self._engine._active_sessions += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if self._transaction_state is not None:
            await self.rollback()
        self._engine._active_sessions = max(0, self._engine._active_sessions - 1)
        self._closed = True
        return False

    async def begin(self) -> None:
        self._ensure_open()
        self._apply_fault()
        self._transaction_state = self._engine._copy_state()

    async def commit(self) -> None:
        self._ensure_open()
        self._apply_fault()
        if self._transaction_state is None:
            return
        self._engine._state = self._transaction_state
        self._transaction_state = None

    async def rollback(self) -> None:
        self._ensure_open(allow_dropped=True)
        self._transaction_state = None

    async def insert(self, table_name: str, row: dict[str, object]) -> None:
        table_rows, schema = self._table(table_name)
        self._apply_fault()
        primary_key = row[schema.primary_key]
        table_rows[primary_key] = deepcopy(row)

    async def get(self, table_name: str, primary_key: object) -> dict[str, object] | None:
        table_rows, _schema = self._table(table_name)
        self._apply_fault()
        row = table_rows.get(primary_key)
        return deepcopy(row) if row is not None else None

    async def all(self, table_name: str) -> list[dict[str, object]]:
        table_rows, schema = self._table(table_name)
        self._apply_fault()
        return [
            deepcopy(table_rows[primary_key])
            for primary_key in sorted(table_rows, key=str)
        ]

    async def update(self, table_name: str, primary_key: object, values: dict[str, object]) -> None:
        table_rows, schema = self._table(table_name)
        self._apply_fault()
        if primary_key not in table_rows:
            raise KeyError(f"no simulated row for {table_name}.{schema.primary_key}={primary_key!r}")
        updated_row = deepcopy(table_rows[primary_key])
        updated_row.update(values)
        table_rows[primary_key] = updated_row

    async def delete(self, table_name: str, primary_key: object) -> None:
        table_rows, schema = self._table(table_name)
        self._apply_fault()
        if primary_key not in table_rows:
            raise KeyError(f"no simulated row for {table_name}.{schema.primary_key}={primary_key!r}")
        del table_rows[primary_key]

    async def execute(self, statement: str) -> None:
        self._ensure_open()
        raise UnsupportedDatabaseOperationError(
            f"raw simulated SQLAlchemy execution is not supported: {statement}"
        )

    def _table(
        self,
        table_name: str,
    ) -> tuple[dict[object, dict[str, object]], TableSchema]:
        self._ensure_open()
        if table_name not in self._engine._schemas:
            raise KeyError(f"unknown simulated table: {table_name}")
        current_state = self._transaction_state or self._engine._state
        return current_state[table_name], self._engine._schemas[table_name]

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
            self._transaction_state = None
            self._dropped = True
            raise DatabaseConnectionDroppedError("simulated database connection dropped")
        if fault.kind == "pool_exhausted":
            raise DatabasePoolExhaustedError("simulated connection pool exhausted")
