"""
shared/generic_fields.py
Generic Gameplay Variables — available to all telemetry families.

These fields are semantically broad gameplay indicators designed to support
unusual or hybrid game mechanics without requiring a new telemetry family.

Design rules
------------
- All fields are optional and nullable. Absent or null → NaN → rules skipped.
- Aggregation strategies are defined here centrally so behaviour is consistent
  across families.
- influence_score is available but kept out of GENERIC_FEATURE_COLS by default.
  Enable it explicitly via INFLUENCE_SCORE_ENABLED if the developer provides
  a clear description of what it measures in their game.
- Generic rules fire alongside family rules but at lower priority.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Field definitions — injected into every family's optional_defaults
# ---------------------------------------------------------------------------

GENERIC_OPTIONAL_DEFAULTS: dict = {
    "objective_progress":   None,   # 0–1  how far toward the level objective
    "system_state_score":   None,   # 0–1  overall game-world state quality
    "positive_action_count": None,  # int  actions that move toward the goal
    "negative_action_count": None,  # int  actions that move away from the goal
    "influence_score":      None,   # 0–1  player effect on another system (opt-in)
    "custom_game_score":    None,   # any  developer-defined numeric score
}

# ---------------------------------------------------------------------------
# Aggregation strategies — how each field is collapsed per session × level
# ---------------------------------------------------------------------------

GENERIC_AGGREGATIONS: dict = {
    # max: captures furthest progress reached, even if player later regressed
    "objective_progress":    "max",
    # last: represents final game-world state at end of session
    "system_state_score":    "last",
    # sum: total count of positive moves across the session
    "positive_action_count": "sum",
    # sum: total count of negative moves across the session
    "negative_action_count": "sum",
    # mean: average influence effect across all actions in the session
    "influence_score":       "mean",
    # last: represents final score at end of session
    "custom_game_score":     "last",
}

# ---------------------------------------------------------------------------
# Feature columns added to every family's FEATURE_COLS
# influence_score excluded by default — opt in via INFLUENCE_SCORE_ENABLED
# ---------------------------------------------------------------------------

GENERIC_FEATURE_COLS: list = [
    "generic_objective_progress",
    "generic_system_state_score",
    "generic_positive_action_count",
    "generic_negative_action_count",
    "generic_custom_game_score",
]

# Set to True (e.g. via env var or config) to include influence_score in ML
INFLUENCE_SCORE_ENABLED: bool = False

# ---------------------------------------------------------------------------
# Thresholds used by the generic rules engine
# ---------------------------------------------------------------------------

GENERIC_THRESHOLDS: dict = {
    "objective_progress_low":        0.4,   # below this → players not reaching goal
    "objective_progress_high":       0.95,  # above this → level may be too easy
    "system_state_score_low":        0.35,  # below this → game world degrading badly
    "action_balance_ratio_high":     0.6,   # negative/(positive+negative) → too many bad moves
    "custom_game_score_low_pct":     0.25,  # bottom quartile of observed scores
    "influence_score_low":           0.2,   # player barely affecting the influence system
}
