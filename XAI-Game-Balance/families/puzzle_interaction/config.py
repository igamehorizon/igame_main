"""
families/puzzle_interaction/config.py
Field definitions for the puzzle_interaction telemetry family.
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
    "interaction_count":       None,
    "wrong_interaction_count": None,
    "hint_count":              None,
}

FEATURE_COLS = [
    "n_actions",
    "mean_decision_time_ms",
    "completion_time_ms",
    "total_interactions",
    "wrong_interaction_rate",
    "hint_rate",
    "retry_count",
    "session_duration_ms",
]
