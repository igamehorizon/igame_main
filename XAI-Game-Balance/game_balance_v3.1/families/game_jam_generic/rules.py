"""
families/game_jam_generic/rules.py
Rule-based recommendations for game_jam_generic.

All rules derive from the 8 base required fields only — no optional data
assumed. Thresholds are tuned for jam context: casual players, short sessions,
high abandonment risk, prototype-quality builds.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def generate_recommendations(
    level_id: str,
    level_df: pd.DataFrame,
    success_rate: float,
    top_features: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    recs: List[Dict[str, str]] = []
    top_names = [f["feature"] for f in top_features]

    def _mean(col: str) -> Optional[float]:
        if col not in level_df.columns:
            return None
        val = level_df[col].mean()
        return None if (val is None or (isinstance(val, float) and np.isnan(val))) else float(val)

    mean_decision   = _mean("mean_decision_time_ms")
    mean_completion = _mean("completion_time_ms")
    mean_duration   = _mean("session_duration_ms")
    mean_retries    = _mean("retry_count")
    n_sessions      = len(level_df)

    # --- Success rate ---
    if success_rate == 0.0:
        recs.append({
            "level_id": level_id,
            "problem": "Zero completions — level may be unbeatable",
            "technical_reason": (
                "No session recorded a success_flag=1 on level_end. "
                "In a jam prototype this often means a missing win-condition trigger "
                "or an unintentional soft-lock."
            ),
            "suggestion": (
                "Verify the win-condition fires correctly in code. "
                "If intentional, add an explicit tutorial or escape hatch."
            ),
            "expected_impact": "Unlocks forward progress for all players immediately.",
            "priority": "high",
        })
    elif success_rate < 0.25:
        recs.append({
            "level_id": level_id,
            "problem": f"Very low completion rate ({success_rate:.1%})",
            "technical_reason": (
                f"Only {success_rate:.1%} of sessions complete this level. "
                "Jam audiences are typically casual and quick to abandon unfair difficulty spikes."
            ),
            "suggestion": (
                "Add a visible hint after 2 failed attempts, reduce required precision, "
                "or shorten the level. Aim for 35–65% completion in a jam context."
            ),
            "expected_impact": "Keeps more players engaged through the full prototype experience.",
            "priority": "high",
        })
    elif success_rate < 0.4:
        recs.append({
            "level_id": level_id,
            "problem": f"Below-target completion rate ({success_rate:.1%})",
            "technical_reason": "Completion is below the 40–65% jam target. Players may be hitting an unjustified skill wall.",
            "suggestion": "Reduce one major obstacle or add a checkpoint mid-level.",
            "expected_impact": "Brings completion rate into the comfortable jam range.",
            "priority": "medium",
        })
    elif success_rate > 0.9:
        recs.append({
            "level_id": level_id,
            "problem": f"Virtually no challenge ({success_rate:.1%} completion)",
            "technical_reason": "High completion with low decision time suggests trivial difficulty.",
            "suggestion": (
                "Add a secondary objective, time pressure, or an optional hard path "
                "to reward skilled players."
            ),
            "expected_impact": "Increases replayability and perceived polish.",
            "priority": "low",
        })

    # --- Decision time ---
    if mean_decision is not None and (mean_decision > 8_000 or "mean_decision_time_ms" in top_names[:2]):
        priority = "high" if mean_decision > 15_000 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"Players hesitate too long per action (avg {mean_decision/1000:.1f} s)",
            "technical_reason": (
                "High mean decision time suggests the level's objective or controls are unclear. "
                "In a jam setting players rarely read instructions."
            ),
            "suggestion": (
                "Add an arrow or highlight on the first correct action. "
                "Simplify the visible option space — remove decorative elements that compete "
                "with interactive ones."
            ),
            "expected_impact": "Reduces confusion-driven abandonment in the first 30 seconds.",
            "priority": priority,
        })

    # --- Retries ---
    if mean_retries is not None and (mean_retries > 3 or "retry_count" in top_names[:2]):
        priority = "high" if mean_retries > 6 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High retry count (avg {mean_retries:.1f} restarts per session)",
            "technical_reason": (
                "Repeated restarts indicate a punishing failure state or an invisible "
                "skill requirement. Jam players expect fast, readable feedback loops."
            ),
            "suggestion": (
                "Make the failure reason explicit on-screen. "
                "Consider adding a mid-level checkpoint or reducing the penalty for failure."
            ),
            "expected_impact": "Converts frustrated quitters into persistent players.",
            "priority": priority,
        })

    # --- Session duration vs completion time mismatch ---
    if (
        mean_duration is not None
        and mean_completion is not None
        and mean_completion > 0
        and mean_duration > mean_completion * 3
        and "session_duration_ms" in top_names[:3]
    ):
        recs.append({
            "level_id": level_id,
            "problem": "Players spend far longer than the level's completion window",
            "technical_reason": (
                f"Average session duration ({mean_duration/1000:.0f} s) is more than 3× "
                f"the average completion time ({mean_completion/1000:.0f} s), "
                "meaning most time is spent stuck or idle."
            ),
            "suggestion": (
                "Introduce an ambient hint system that activates after inactivity "
                "exceeds twice the expected completion time."
            ),
            "expected_impact": "Reduces idle drop-off and guides players toward the solution.",
            "priority": "medium",
        })

    # --- Small sample warning ---
    if n_sessions < 5:
        recs.append({
            "level_id": level_id,
            "problem": f"Very few playtests recorded ({n_sessions} session{'s' if n_sessions != 1 else ''})",
            "technical_reason": (
                "Statistical reliability is low with fewer than 5 sessions. "
                "Results may not reflect the broader player experience."
            ),
            "suggestion": (
                "Run at least 5 more playtests before acting on these recommendations. "
                "Share the build via a jam-testing Discord or itch.io early-access page."
            ),
            "expected_impact": "Higher confidence in data-driven design decisions.",
            "priority": "low",
        })

    if not recs:
        recs.append({
            "level_id": level_id,
            "problem": "No significant issues detected",
            "technical_reason": "All base metrics are within healthy thresholds for a jam prototype.",
            "suggestion": "Polish visual feedback and audio cues to elevate the jam impression.",
            "expected_impact": "Stronger presentation score during judging.",
            "priority": "low",
        })

    return recs[:4]
