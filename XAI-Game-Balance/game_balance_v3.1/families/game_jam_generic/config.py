"""
families/game_jam_generic/config.py
Field definitions for the game_jam_generic telemetry family.

No optional fields — designed for jam prototypes where only the universal
base fields are guaranteed. All analysis derives from decision time,
completion time, success, and session structure alone.
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

OPTIONAL_DEFAULTS = {}

FEATURE_COLS = [
    "n_actions",
    "mean_decision_time_ms",
    "completion_time_ms",
    "retry_count",
    "session_duration_ms",
    "success_rate_within_session",
]
