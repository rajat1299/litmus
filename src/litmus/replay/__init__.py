from litmus.replay.differential import (
    DifferentialReplayResult,
    ReplayClassification,
    run_differential_replay,
)
from litmus.replay.trace import (
    ReplayTraceRecord,
    load_replay_trace_records,
    replay_trace_record_from_dict,
    replay_trace_record_to_dict,
    replay_trace_path,
    save_replay_trace_records,
)


def replay_record_for_seed(root, seed):
    from litmus.runs.store import replay_record_for_seed as replay_record_for_seed_from_runs

    _run, record = replay_record_for_seed_from_runs(root, seed)
    return record

__all__ = [
    "DifferentialReplayResult",
    "ReplayClassification",
    "ReplayTraceRecord",
    "load_replay_trace_records",
    "replay_record_for_seed",
    "replay_trace_record_from_dict",
    "replay_trace_record_to_dict",
    "replay_trace_path",
    "run_differential_replay",
    "save_replay_trace_records",
]
