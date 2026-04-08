from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from litmus.dst.runtime import TraceEvent


LAUNCH_COMPATIBILITY_MATRIX: dict[str, object] = {
    "python": "3.11+",
    "asgi": "FastAPI / Starlette-style ASGI apps",
    "http": {
        "package": "httpx/aiohttp",
        "supported_shapes": ["httpx/aiohttp"],
    },
    "sqlalchemy": {
        "package": "sqlalchemy.ext.asyncio/sqlalchemy.orm",
        "supported_shapes": [
            "sqlalchemy.ext.asyncio.create_async_engine",
            "sqlalchemy.ext.asyncio.async_sessionmaker",
            "sqlalchemy.ext.asyncio.AsyncSession",
            "sqlalchemy.orm.sessionmaker(class_=AsyncSession)",
        ],
    },
    "redis": {
        "package": "redis.asyncio",
        "supported_shapes": [
            "redis.asyncio.Redis",
            "redis.asyncio.Redis.from_url",
            "redis.asyncio.client.Redis",
            "redis.asyncio.client.Redis.from_url",
        ],
    },
}

BOUNDARY_ORDER = ("http", "sqlalchemy", "redis")


@dataclass(slots=True)
class BoundaryCompatibility:
    status: str = "not_detected"
    detected: bool = False
    intercepted: bool = False
    simulated: bool = False
    faulted: bool = False
    unsupported: bool = False
    supported_shapes: list[str] = field(default_factory=list)
    unsupported_details: list[str] = field(default_factory=list)

    def finalize(self) -> None:
        if self.unsupported and (self.simulated or self.intercepted):
            self.status = "partial"
        elif self.unsupported:
            self.status = "unsupported"
        elif self.simulated or self.intercepted:
            self.status = "supported"
        elif self.detected:
            self.status = "detected_only"
        else:
            self.status = "not_detected"

    def merge(self, other: BoundaryCompatibility) -> None:
        self.detected = self.detected or other.detected
        self.intercepted = self.intercepted or other.intercepted
        self.simulated = self.simulated or other.simulated
        self.faulted = self.faulted or other.faulted
        self.unsupported = self.unsupported or other.unsupported
        for shape in other.supported_shapes:
            if shape not in self.supported_shapes:
                self.supported_shapes.append(shape)
        for detail in other.unsupported_details:
            if detail not in self.unsupported_details:
                self.unsupported_details.append(detail)
        self.finalize()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "detected": self.detected,
            "intercepted": self.intercepted,
            "simulated": self.simulated,
            "faulted": self.faulted,
            "unsupported": self.unsupported,
            "supported_shapes": list(self.supported_shapes),
            "unsupported_details": list(self.unsupported_details),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> BoundaryCompatibility:
        compatibility = cls(
            status=str(payload.get("status", "not_detected")),
            detected=bool(payload.get("detected", False)),
            intercepted=bool(payload.get("intercepted", False)),
            simulated=bool(payload.get("simulated", False)),
            faulted=bool(payload.get("faulted", False)),
            unsupported=bool(payload.get("unsupported", False)),
            supported_shapes=list(payload.get("supported_shapes", [])),
            unsupported_details=list(payload.get("unsupported_details", [])),
        )
        compatibility.finalize()
        return compatibility


@dataclass(slots=True)
class CompatibilityReport:
    matrix: dict[str, object]
    boundaries: dict[str, BoundaryCompatibility]

    def to_dict(self) -> dict[str, object]:
        return {
            "matrix": _copy_mapping(self.matrix),
            "boundaries": {
                boundary: compatibility.to_dict()
                for boundary, compatibility in self.boundaries.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CompatibilityReport:
        boundaries_payload = payload.get("boundaries", {})
        boundaries = _empty_boundaries()
        for boundary, compatibility_payload in boundaries_payload.items():
            boundaries[boundary] = BoundaryCompatibility.from_dict(dict(compatibility_payload))
        return cls(
            matrix=_copy_mapping(payload.get("matrix", _copy_matrix())),
            boundaries=boundaries,
        )


def compatibility_report_from_trace(trace: list[TraceEvent]) -> CompatibilityReport:
    boundaries = _empty_boundaries()
    for event in trace:
        boundary = str(event.metadata.get("boundary", event.metadata.get("target", ""))).lower()
        if boundary not in boundaries:
            continue
        compatibility = boundaries[boundary]
        if event.kind == "boundary_detected":
            compatibility.detected = True
        elif event.kind == "boundary_intercepted":
            compatibility.detected = True
            compatibility.intercepted = True
            shape = str(event.metadata.get("supported_shape", "")).strip()
            if shape and shape not in compatibility.supported_shapes:
                compatibility.supported_shapes.append(shape)
        elif event.kind == "boundary_simulated":
            compatibility.detected = True
            compatibility.intercepted = True
            compatibility.simulated = True
        elif event.kind == "boundary_unsupported":
            compatibility.detected = True
            compatibility.unsupported = True
            detail = str(event.metadata.get("detail", "")).strip()
            if detail and detail not in compatibility.unsupported_details:
                compatibility.unsupported_details.append(detail)
        elif event.kind == "fault_injected":
            compatibility.faulted = True
        compatibility.finalize()
    return CompatibilityReport(matrix=_copy_matrix(), boundaries=boundaries)


def compatibility_report_from_result(result) -> CompatibilityReport:
    aggregate = CompatibilityReport(matrix=_copy_matrix(), boundaries=_empty_boundaries())
    for record in result.replay_traces:
        report = compatibility_report_from_trace(record.trace)
        for boundary, compatibility in report.boundaries.items():
            aggregate.boundaries[boundary].merge(compatibility)
    return aggregate


def render_compatibility_lines(report: CompatibilityReport) -> list[str]:
    return [
        f"- {boundary}: {render_compatibility_status(compatibility)}"
        for boundary, compatibility in report.boundaries.items()
    ]


def render_compatibility_markdown_lines(report: CompatibilityReport) -> list[str]:
    return [
        f"- `{boundary}`: {render_compatibility_status(compatibility, markdown=True)}"
        for boundary, compatibility in report.boundaries.items()
    ]


def render_compatibility_status(
    compatibility: BoundaryCompatibility,
    *,
    markdown: bool = False,
) -> str:
    if compatibility.status == "partial":
        detail = compatibility.unsupported_details[0] if compatibility.unsupported_details else None
        if detail is None:
            return "partial (supported + unsupported)"
        if markdown:
            return f"partial (`supported` + `unsupported`: `{detail}`)"
        return f"partial (supported + unsupported: {detail})"
    if compatibility.status == "unsupported":
        detail = compatibility.unsupported_details[0] if compatibility.unsupported_details else None
        if detail is None:
            return "unsupported"
        if markdown:
            return f"unsupported (`{detail}`)"
        return f"unsupported ({detail})"
    if compatibility.status == "supported":
        return "supported"
    if compatibility.status == "detected_only":
        return "detected only"
    return "not detected"


def replay_compatibility_lines(trace: list[TraceEvent]) -> list[str]:
    report = compatibility_report_from_trace(trace)
    return [
        f"Compatibility {boundary}: {render_compatibility_status(compatibility)}."
        for boundary, compatibility in report.boundaries.items()
        if compatibility.status != "not_detected"
    ]


def _copy_matrix() -> dict[str, object]:
    return _copy_mapping(LAUNCH_COMPATIBILITY_MATRIX)


def _copy_mapping(source: dict[str, object]) -> dict[str, object]:
    copied: dict[str, object] = {}
    for key, value in source.items():
        if isinstance(value, dict):
            copied[key] = {
                inner_key: list(inner_value) if isinstance(inner_value, list) else inner_value
                for inner_key, inner_value in value.items()
            }
        else:
            copied[key] = value
    return copied


def _empty_boundaries() -> dict[str, BoundaryCompatibility]:
    return {
        boundary: BoundaryCompatibility()
        for boundary in BOUNDARY_ORDER
    }
