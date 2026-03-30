from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from hypothesis import HealthCheck, find, settings
from hypothesis.errors import NoSuchExample
from hypothesis import strategies as st

from litmus.invariants.models import Invariant, InvariantStatus, InvariantType, RequestExample


class PropertyCheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class PropertyCheckResult:
    invariant: Invariant
    status: PropertyCheckStatus
    failing_request: RequestExample | None = None
    reason: str | None = None


PropertyChecker = Callable[[Invariant, RequestExample], bool]


def run_property_checks(
    invariants: list[Invariant],
    checker: PropertyChecker,
    max_examples: int = 100,
) -> list[PropertyCheckResult]:
    results: list[PropertyCheckResult] = []

    for invariant in invariants:
        skip_reason = _skip_reason(invariant)
        if skip_reason is not None:
            results.append(
                PropertyCheckResult(
                    invariant=invariant,
                    status=PropertyCheckStatus.SKIPPED,
                    reason=skip_reason,
                )
            )
            continue

        request_strategy = _request_strategy(invariant.request)

        try:
            failing_request = find(
                request_strategy,
                lambda request: not checker(invariant, request),
                settings=settings(
                    max_examples=max_examples,
                    database=None,
                    derandomize=True,
                    suppress_health_check=[HealthCheck.too_slow],
                ),
            )
        except NoSuchExample:
            results.append(
                PropertyCheckResult(
                    invariant=invariant,
                    status=PropertyCheckStatus.PASSED,
                )
            )
            continue

        results.append(
            PropertyCheckResult(
                invariant=invariant,
                status=PropertyCheckStatus.FAILED,
                failing_request=failing_request,
            )
        )

    return results


def _skip_reason(invariant: Invariant) -> str | None:
    if invariant.status is not InvariantStatus.CONFIRMED:
        return "only confirmed invariants can run as property checks"
    if invariant.type is not InvariantType.PROPERTY:
        return "only property invariants can run in the property layer"
    if invariant.request is None:
        return "property invariants need a request example to generate inputs"
    return None


def _request_strategy(request: RequestExample) -> st.SearchStrategy[RequestExample]:
    return st.builds(
        RequestExample,
        method=st.just(request.method),
        path=st.just(request.path),
        payload=_value_strategy(request.payload),
    )


def _value_strategy(value: Any) -> st.SearchStrategy[Any]:
    if value is None:
        return st.none()
    if isinstance(value, bool):
        return st.booleans()
    if isinstance(value, int):
        if value >= 0:
            return st.integers(min_value=0, max_value=max(value * 2, 10))
        return st.integers(min_value=value * 2, max_value=max(value, 0))
    if isinstance(value, float):
        magnitude = max(abs(value), 1.0)
        return st.floats(
            min_value=-magnitude * 2,
            max_value=magnitude * 2,
            allow_nan=False,
            allow_infinity=False,
        )
    if isinstance(value, str):
        return st.text(min_size=0, max_size=max(len(value) + 4, 4))
    if isinstance(value, dict):
        return st.fixed_dictionaries({key: _value_strategy(item) for key, item in value.items()})
    if isinstance(value, list):
        if not value:
            return st.lists(st.none(), max_size=3)
        return st.lists(_value_strategy(value[0]), min_size=len(value), max_size=max(len(value), 3))
    return st.just(value)
