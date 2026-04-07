from __future__ import annotations

from datetime import datetime

from litmus.config import FaultProfile

LOCAL_VERIFY_BUDGET_MS = 10_000
CI_VERIFY_BUDGET_MS = 60_000
LOCAL_PROPERTY_MAX_EXAMPLES = 100
CI_PROPERTY_MAX_EXAMPLES = 500
LOCAL_REPLAY_SEEDS_PER_SCENARIO = 3
CI_REPLAY_SEEDS_PER_SCENARIO = 500


def budget_policy_for_mode(
    mode: object,
    *,
    fault_profile: FaultProfile | str = FaultProfile.DEFAULT,
) -> str:
    resolved_mode = coerce_run_mode(mode)
    resolved_fault_profile = coerce_fault_profile(fault_profile)
    if resolved_mode == "ci":
        return "ci_deeper"
    if resolved_mode == "mcp":
        return "mcp_local_agent"
    if resolved_mode == "watch":
        return "watch_local_iteration"
    if resolved_fault_profile is FaultProfile.HOSTILE:
        return "local_deeper_opt_in"
    if resolved_fault_profile is FaultProfile.GENTLE:
        return "launch_lighter"
    return "launch_default"


def verify_budget_ms_for_mode(mode: object) -> int:
    resolved_mode = coerce_run_mode(mode)
    if resolved_mode == "ci":
        return CI_VERIFY_BUDGET_MS
    return LOCAL_VERIFY_BUDGET_MS


def property_max_examples_for_mode(
    mode: object,
    *,
    fault_profile: FaultProfile | str = FaultProfile.DEFAULT,
) -> int:
    resolved_mode = coerce_run_mode(mode)
    resolved_fault_profile = coerce_fault_profile(fault_profile)
    if resolved_mode == "ci":
        return CI_PROPERTY_MAX_EXAMPLES
    if resolved_fault_profile is FaultProfile.GENTLE:
        return 25
    if resolved_fault_profile is FaultProfile.HOSTILE:
        return 250
    return LOCAL_PROPERTY_MAX_EXAMPLES


def replay_seed_count_for_mode(
    mode: object,
    *,
    fault_profile: FaultProfile | str = FaultProfile.DEFAULT,
) -> int:
    resolved_mode = coerce_run_mode(mode)
    resolved_fault_profile = coerce_fault_profile(fault_profile)
    if resolved_mode == "ci":
        return CI_REPLAY_SEEDS_PER_SCENARIO
    if resolved_fault_profile is FaultProfile.GENTLE:
        return 1
    if resolved_fault_profile is FaultProfile.HOSTILE:
        return 9
    return LOCAL_REPLAY_SEEDS_PER_SCENARIO


def elapsed_ms(started_at: str | None, completed_at: str | None) -> int | None:
    if started_at is None or completed_at is None:
        return None
    started = datetime.fromisoformat(started_at)
    completed = datetime.fromisoformat(completed_at)
    return max(0, int((completed - started).total_seconds() * 1000))


def coerce_run_mode(mode: object) -> str:
    if hasattr(mode, "value"):
        return str(getattr(mode, "value"))
    return str(mode)


def coerce_fault_profile(fault_profile: FaultProfile | str) -> FaultProfile:
    if isinstance(fault_profile, FaultProfile):
        return fault_profile
    return FaultProfile(fault_profile)
