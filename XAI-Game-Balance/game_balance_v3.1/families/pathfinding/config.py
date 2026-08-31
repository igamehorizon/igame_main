"""
families/pathfinding/config.py
Field definitions for the pathfinding telemetry family.
"""

REQUIRED_FIELDS = [
    "timestamp",
    "session_id",
    "player_id",
    "level_id",
    "event_type",
    "decision_time_ms",
    "completion_time_ms",
    "success_flag",
]

OPTIONAL_DEFAULTS = {
    "was_backtracked": None,
    "moves":           None,
    "timeout_flag":    None,
    "nodes_expanded":  None,
}

FEATURE_COLS = [
    "n_actions",
    "mean_decision_time_ms",
    "completion_time_ms",
    "backtrack_rate",
    "total_moves",
    "timeout_rate",
    "mean_nodes_expanded",
    "retry_count",
    "session_duration_ms",
]
