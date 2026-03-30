from __future__ import annotations

import asyncio
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from litmus.dst.faults import FaultPlan, FaultSpec


class RedisConnectionRefusedError(Exception):
    pass


class RedisTimeoutError(Exception):
    pass


class UnsupportedRedisOperationError(Exception):
    pass


class RedisPartialWriteError(Exception):
    def __init__(self, applied_count: int) -> None:
        self.applied_count = applied_count
        super().__init__(f"simulated redis partial write after {applied_count} value(s)")


class RedisMovedError(Exception):
    def __init__(self, slot: int, location: str) -> None:
        self.slot = slot
        self.location = location
        super().__init__(f"MOVED {slot} {location}")


@dataclass(slots=True)
class _RedisEntry:
    kind: str
    value: Any
    expires_at: float | None = None


@dataclass(slots=True)
class _BlockingPopWaiter:
    key: str
    deadline: float
    future: asyncio.Future[tuple[str, Any] | None]


class SimulatedRedis:
    def __init__(self, fault_plan: FaultPlan | None = None) -> None:
        self._entries: dict[str, _RedisEntry] = {}
        self._fault_plan = fault_plan or FaultPlan(seed=0)
        self._step = 0
        self._now = 0.0
        self._waiters: dict[str, list[_BlockingPopWaiter]] = defaultdict(list)

    async def get(self, key: str) -> Any | None:
        self._expire_due_keys()
        self._apply_fault()
        entry = self._entry(key, expected_kind="string", allow_missing=True)
        return deepcopy(entry.value) if entry is not None else None

    async def set(self, key: str, value: Any) -> bool:
        self._expire_due_keys()
        self._apply_fault()
        self._entries[key] = _RedisEntry(kind="string", value=deepcopy(value))
        return True

    async def setex(self, key: str, ttl_seconds: int | float, value: Any) -> bool:
        self._expire_due_keys()
        self._apply_fault()
        self._entries[key] = _RedisEntry(
            kind="string",
            value=deepcopy(value),
            expires_at=self._now + float(ttl_seconds),
        )
        return True

    async def incr(self, key: str) -> int:
        self._expire_due_keys()
        self._apply_fault()
        entry = self._entry(key, expected_kind="string", allow_missing=True)
        current_value = None if entry is None else entry.value
        next_value = 1 if current_value is None else int(current_value) + 1
        self._entries[key] = _RedisEntry(kind="string", value=next_value)
        return next_value

    async def delete(self, *keys: str) -> int:
        self._expire_due_keys()
        self._apply_fault()
        deleted_count = 0
        for key in keys:
            if key in self._entries:
                del self._entries[key]
                deleted_count += 1
        return deleted_count

    async def hset(self, key: str, field: str, value: Any) -> int:
        self._expire_due_keys()
        self._apply_fault()
        entry = self._hash_entry(key, create=True)
        assert entry is not None
        is_new_field = field not in entry.value
        entry.value[field] = deepcopy(value)
        return 1 if is_new_field else 0

    async def hget(self, key: str, field: str) -> Any | None:
        self._expire_due_keys()
        self._apply_fault()
        entry = self._hash_entry(key, create=False)
        if entry is None:
            return None
        return deepcopy(entry.value.get(field))

    async def hgetall(self, key: str) -> dict[str, Any]:
        self._expire_due_keys()
        self._apply_fault()
        entry = self._hash_entry(key, create=False)
        if entry is None:
            return {}
        return deepcopy(entry.value)

    async def lpush(self, key: str, *values: Any) -> int:
        return await self._push(key, values, left=True)

    async def rpush(self, key: str, *values: Any) -> int:
        return await self._push(key, values, left=False)

    async def lpop(self, key: str) -> Any | None:
        self._expire_due_keys()
        self._apply_fault()
        entry = self._list_entry(key, create=False)
        if entry is None or not entry.value:
            return None
        value = entry.value.pop(0)
        if not entry.value:
            self._entries.pop(key, None)
        return deepcopy(value)

    async def brpop(self, key: str, timeout: int | float) -> tuple[str, Any] | None:
        self._expire_due_keys()
        self._apply_fault()

        entry = self._list_entry(key, create=False)
        if entry is not None and entry.value:
            value = entry.value.pop()
            if not entry.value:
                self._entries.pop(key, None)
            return key, deepcopy(value)

        if timeout <= 0:
            return None

        future: asyncio.Future[tuple[str, Any] | None] = asyncio.get_running_loop().create_future()
        self._waiters[key].append(
            _BlockingPopWaiter(
                key=key,
                deadline=self._now + float(timeout),
                future=future,
            )
        )
        return await future

    async def advance_time(self, seconds: int | float) -> None:
        self._now += float(seconds)
        self._expire_due_keys()
        self._resolve_waiter_timeouts()
        await asyncio.sleep(0)

    async def publish(self, channel: str, message: Any) -> None:
        raise UnsupportedRedisOperationError(
            f"redis pub/sub is not implemented in this checkpoint: publish({channel!r}, ...)"
        )

    async def subscribe(self, channel: str) -> None:
        raise UnsupportedRedisOperationError(
            f"redis pub/sub is not implemented in this checkpoint: subscribe({channel!r})"
        )

    async def _push(self, key: str, values: tuple[Any, ...], left: bool) -> int:
        self._expire_due_keys()
        fault = self._apply_fault(allow_partial_write=True)

        values_to_apply = values
        partial_applied_count: int | None = None
        if fault is not None and fault.kind == "partial_write":
            partial_applied_count = max(0, min(len(values), int(fault.params.get("applied_count", 1))))
            values_to_apply = values[:partial_applied_count]

        entry = self._list_entry(key, create=bool(values_to_apply))

        if entry is not None:
            for value in values_to_apply:
                if left:
                    entry.value.insert(0, deepcopy(value))
                else:
                    entry.value.append(deepcopy(value))

            self._deliver_blocking_pops(key)

        if partial_applied_count is not None:
            raise RedisPartialWriteError(applied_count=partial_applied_count)

        return 0 if entry is None else len(entry.value)

    def _entry(
        self,
        key: str,
        expected_kind: str,
        allow_missing: bool,
    ) -> _RedisEntry | None:
        entry = self._entries.get(key)
        if entry is None:
            if allow_missing:
                return None
            raise KeyError(f"missing simulated redis key: {key}")
        if entry.kind != expected_kind:
            raise UnsupportedRedisOperationError(
                f"redis key {key!r} stores {entry.kind}, not {expected_kind}"
            )
        return entry

    def _hash_entry(self, key: str, create: bool) -> _RedisEntry | None:
        entry = self._entries.get(key)
        if entry is None:
            if not create:
                return None
            entry = _RedisEntry(kind="hash", value={})
            self._entries[key] = entry
            return entry
        if entry.kind != "hash":
            raise UnsupportedRedisOperationError(f"redis key {key!r} is not a hash")
        return entry

    def _list_entry(self, key: str, create: bool) -> _RedisEntry | None:
        entry = self._entries.get(key)
        if entry is None:
            if not create:
                return None
            entry = _RedisEntry(kind="list", value=[])
            self._entries[key] = entry
            return entry
        if entry.kind != "list":
            raise UnsupportedRedisOperationError(f"redis key {key!r} is not a list")
        return entry

    def _expire_due_keys(self) -> None:
        expired_keys = [
            key
            for key, entry in self._entries.items()
            if entry.expires_at is not None and entry.expires_at <= self._now
        ]
        for key in expired_keys:
            self._entries.pop(key, None)

    def _deliver_blocking_pops(self, key: str) -> None:
        if key not in self._waiters:
            return

        entry = self._list_entry(key, create=False)
        if entry is None:
            return

        active_waiters: list[_BlockingPopWaiter] = []
        for waiter in self._waiters[key]:
            if waiter.future.done():
                continue
            if not entry.value:
                active_waiters.append(waiter)
                continue
            value = entry.value.pop()
            waiter.future.set_result((key, deepcopy(value)))

        self._waiters[key] = active_waiters
        if not entry.value:
            self._entries.pop(key, None)
        if not self._waiters[key]:
            self._waiters.pop(key, None)

    def _resolve_waiter_timeouts(self) -> None:
        for key, waiters in list(self._waiters.items()):
            active_waiters: list[_BlockingPopWaiter] = []
            for waiter in waiters:
                if waiter.future.done():
                    continue
                if waiter.deadline <= self._now:
                    waiter.future.set_result(None)
                    continue
                active_waiters.append(waiter)
            if active_waiters:
                self._waiters[key] = active_waiters
            else:
                self._waiters.pop(key, None)

    def _next_fault(self) -> FaultSpec | None:
        self._step += 1
        return self._fault_plan.fault_for_step(self._step)

    def _apply_fault(self, allow_partial_write: bool = False) -> FaultSpec | None:
        fault = self._next_fault()
        if fault is None or fault.target not in {"redis", "redis.asyncio", "cache"}:
            return None

        if fault.kind == "connection_refused":
            raise RedisConnectionRefusedError("simulated redis connection refused")
        if fault.kind == "timeout":
            raise RedisTimeoutError("simulated redis timeout")
        if fault.kind == "moved":
            raise RedisMovedError(
                slot=int(fault.params.get("slot", 0)),
                location=str(fault.params.get("location", "127.0.0.1:6379")),
            )
        if fault.kind == "partial_write" and allow_partial_write:
            return fault
        return None
