"""
families/accessibility_precision/config.py
Field definitions for the Accessibility / Precision telemetry family.

Purpose
-------
Measures interaction friction, precision difficulty, hesitation, and support
usage. Not intended to diagnose accessibility needs — it measures observable
gameplay behaviour that may indicate friction or difficulty with precision tasks.

All family-specific fields are optional and nullable following the v2.5 pattern.
Missing or null values are left as NaN and rules that depend on them are skipped.

Derived rates (computed by extractor, not recorded by developer)
---------------------------------------------------------------
- error_rate        = error_count / n_actions
- assistance_rate   = assistance_used / n_actions
- undo_rate         = undo_count / n_actions

Rates are event-normalised (per event/action), not interaction-normalised.
Only computed when n_actions > 0.
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
    "error_count":           None,  # int   — incorrect interactions or precision mistakes
    "assistance_used":       None,  # int   — assistance features used (hints, snap, zoom, etc.)
    "idle_time_ms":          None,  # float — longest inactivity period during the task (ms)
    "input_precision_score": None,  # 0–1   — game-defined normalised precision score
    "undo_count":            None,  # int   — undo or correction actions taken
}

FEATURE_COLS = [
    "n_actions",
    "mean_decision_time_ms",
    "completion_time_ms",
    "total_errors",
    "error_rate",               # event-normalised: error_count / n_actions
    "total_assistance",
    "assistance_rate",          # event-normalised: assistance_used / n_actions
    "max_idle_time_ms",
    "mean_input_precision_score",
    "total_undos",
    "undo_rate",                # event-normalised: undo_count / n_actions
    "retry_count",
    "session_duration_ms",
]
