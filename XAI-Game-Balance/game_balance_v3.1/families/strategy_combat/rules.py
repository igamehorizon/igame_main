"""
families/strategy_combat/rules.py
Rule-based recommendations for the strategy_combat family.
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

    mean_deaths          = _mean("total_deaths")
    mean_damage_per_move = _mean("damage_per_move")
    mean_resource_loss   = _mean("total_resource_loss")
    mean_heal_ratio      = _mean("healing_to_damage_ratio")
    mean_decision        = _mean("mean_decision_time_ms")
    mean_retries         = _mean("retry_count")

    # --- Success rate (always available) ---
    if success_rate == 0.0:
        recs.append({
            "level_id": level_id,
            "problem": "No players cleared this encounter",
            "technical_reason": "Zero completions — the encounter may be mathematically unwinnable with current player stats or enemy scaling.",
            "suggestion": "Run a damage/TTK audit. Check whether the encounter can be cleared with average resources and no deaths.",
            "expected_impact": "Reveals whether the issue is a tuning error or a fundamental design problem.",
            "priority": "high",
        })
    elif success_rate < 0.3:
        recs.append({
            "level_id": level_id,
            "problem": f"Low clear rate ({success_rate:.1%})",
            "technical_reason": f"Only {success_rate:.1%} of sessions result in a clear. Encounter difficulty exceeds player capability.",
            "suggestion": "Reduce enemy damage output by 10–15%, increase player resource availability, or add a recovery window after the first death.",
            "expected_impact": "Raises clear rate toward the 40–60% target without removing tension.",
            "priority": "high",
        })
    elif success_rate > 0.88:
        recs.append({
            "level_id": level_id,
            "problem": f"Encounter too easy ({success_rate:.1%} clear rate)",
            "technical_reason": "Very high clear rate with low damage taken suggests the encounter poses no meaningful threat.",
            "suggestion": "Increase enemy aggression, add a secondary mechanic, or reduce player healing availability.",
            "expected_impact": "Restores tension and makes victory feel earned.",
            "priority": "medium",
        })

    # --- Deaths (optional field) ---
    if mean_deaths is not None and (mean_deaths > 2 or "total_deaths" in top_names[:2]):
        priority = "high" if mean_deaths > 5 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High death count (avg {mean_deaths:.1f} deaths per session)",
            "technical_reason": (
                "Repeated deaths suggest a specific moment or enemy is disproportionately lethal. "
                "Players may lack the resources or information to survive it."
            ),
            "suggestion": "Add a death recap showing what killed the player. Reduce the spike damage of the most lethal source by 10–20%.",
            "expected_impact": "Players understand failure and are motivated to retry rather than quit.",
            "priority": priority,
        })

    # --- Damage per move (optional derived field) ---
    if mean_damage_per_move is not None and (mean_damage_per_move > 15 or "damage_per_move" in top_names[:2]):
        priority = "high" if mean_damage_per_move > 30 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High damage pressure (avg {mean_damage_per_move:.1f} damage per action)",
            "technical_reason": "Each player action results in disproportionate incoming damage, leaving no room for strategic play.",
            "suggestion": "Introduce brief windows of reduced enemy activity after key player actions to reward good timing.",
            "expected_impact": "Creates a rhythm of threat and relief, improving the combat feel.",
            "priority": priority,
        })

    # --- Resource loss (optional field) ---
    if mean_resource_loss is not None and "total_resource_loss" in top_names[:3]:
        priority = "high" if "total_resource_loss" == top_names[0] else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High resource loss (avg {mean_resource_loss:.1f} per session)",
            "technical_reason": "Players exhaust resources at a rate that will leave them underpowered in subsequent encounters.",
            "suggestion": "Add a minor resource cache mid-encounter, or reduce the resource cost of defensive actions.",
            "expected_impact": "Prevents resource starvation from compounding difficulty across the session.",
            "priority": priority,
        })

    # --- Healing dependency (optional derived field) ---
    if mean_heal_ratio is not None and (mean_heal_ratio > 0.8 or "healing_to_damage_ratio" in top_names[:2]):
        recs.append({
            "level_id": level_id,
            "problem": f"Over-reliance on healing (heal/damage ratio: {mean_heal_ratio:.2f})",
            "technical_reason": (
                "Players use healing almost as fast as they take damage, "
                "suggesting the encounter is a war of attrition rather than a skill test."
            ),
            "suggestion": "Introduce a mechanic that rewards damage avoidance (e.g. bonus on no-hit windows) rather than healing recovery.",
            "expected_impact": "Shifts player strategy from reactive healing to proactive positioning.",
            "priority": "medium",
        })

    # --- Decision time (required field) ---
    if mean_decision is not None and (mean_decision > 8_000 or "mean_decision_time_ms" in top_names[:2]):
        recs.append({
            "level_id": level_id,
            "problem": f"Slow decision-making (avg {mean_decision/1000:.1f} s per action)",
            "technical_reason": "Long pauses before actions in a combat context suggest UI overload or unclear ability affordances.",
            "suggestion": "Simplify the action UI — surface the 3 most relevant abilities based on context and hide the rest.",
            "expected_impact": "Reduces decision paralysis and makes combat feel more fluid.",
            "priority": "medium",
        })

    # --- Retries (derived, always present) ---
    if mean_retries is not None and (mean_retries > 3 or "retry_count" in top_names[:2]):
        priority = "high" if mean_retries > 6 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High retry count (avg {mean_retries:.1f} restarts)",
            "technical_reason": "Repeated restarts indicate a punishing failure state or an invisible skill wall.",
            "suggestion": "Show a post-death summary with the top damage source. Consider a soft checkpoint after 50% of enemies are cleared.",
            "expected_impact": "Converts frustrated quitters into persistent players.",
            "priority": priority,
        })

    if not recs:
        recs.append({
            "level_id": level_id,
            "problem": "No significant issues detected",
            "technical_reason": "All strategy/combat metrics are within acceptable thresholds.",
            "suggestion": "Consider adding an optional challenge modifier (e.g. no-healing run) to reward skilled players.",
            "expected_impact": "Increases replayability without affecting the default difficulty.",
            "priority": "low",
        })

    return recs[:4]
