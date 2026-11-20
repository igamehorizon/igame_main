"""
families/strategy_combat/config.py
Field definitions for the strategy_combat telemetry family.
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
    "moves":          None,
    "damage_taken":   None,
    "deaths":         None,
    "resource_loss":  None,
    "healing_usage":  None,
}

FEATURE_COLS = [
    "n_actions",
    "mean_decision_time_ms",
    "completion_time_ms",
    "total_moves",
    "total_damage_taken",
    "total_deaths",
    "total_resource_loss",
    "total_healing_usage",
    "damage_per_move",
    "healing_to_damage_ratio",
    "retry_count",
    "session_duration_ms",
]
