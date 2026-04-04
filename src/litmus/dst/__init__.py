from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "AsgiExecutionResult": ("litmus.dst.asgi", "AsgiExecutionResult"),
    "DeterministicScheduler": ("litmus.dst.scheduler", "DeterministicScheduler"),
    "FaultPlan": ("litmus.dst.faults", "FaultPlan"),
    "FaultSpec": ("litmus.dst.faults", "FaultSpec"),
    "RuntimeContext": ("litmus.dst.runtime", "RuntimeContext"),
    "TraceEvent": ("litmus.dst.runtime", "TraceEvent"),
    "build_fault_plan": ("litmus.dst.faults", "build_fault_plan"),
    "run_asgi_app": ("litmus.dst.asgi", "run_asgi_app"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = export
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals()) + __all__)
