"""
families/pathfinding/rules.py
Rule-based recommendations for the pathfinding family.
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

    mean_backtrack = _mean("backtrack_rate")
    mean_decision  = _mean("mean_decision_time_ms")
    mean_timeout   = _mean("timeout_rate")
    mean_nodes     = _mean("mean_nodes_expanded")
    mean_retries   = _mean("retry_count")

    # --- Success rate (always available) ---
    if success_rate == 0.0:
        recs.append({
            "level_id": level_id,
            "problem": "No players completed this level",
            "technical_reason": "Success rate is 0% — the level may be unsolvable or contain a soft-lock.",
            "suggestion": "Verify the win-condition trigger fires correctly. Reduce branching factor or add a tutorial hint.",
            "expected_impact": "Eliminates a complete drop-off point and allows players to progress.",
            "priority": "high",
        })
    elif success_rate < 0.3:
        recs.append({
            "level_id": level_id,
            "problem": f"Low completion rate ({success_rate:.1%})",
            "technical_reason": f"Only {success_rate:.1%} of sessions complete this level, well below the 40–60% target.",
            "suggestion": "Reduce required steps, add intermediate checkpoints, or lower the penalty for mistakes.",
            "expected_impact": "Raises completion rate toward the 40–60% target range.",
            "priority": "high",
        })
    elif success_rate > 0.85:
        recs.append({
            "level_id": level_id,
            "problem": f"Level too easy ({success_rate:.1%} completion)",
            "technical_reason": "Very high success rate suggests insufficient navigational challenge.",
            "suggestion": "Add dead-end branches, reduce visible waypoints, or tighten the move budget.",
            "expected_impact": "Brings challenge into the 50–70% target range.",
            "priority": "medium",
        })

    # --- Backtrack rate (optional field) ---
    if mean_backtrack is not None and (mean_backtrack > 0.3 or "backtrack_rate" in top_names[:2]):
        priority = "high" if mean_backtrack > 0.5 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High backtrack rate ({mean_backtrack:.1%})",
            "technical_reason": "Players frequently reverse direction, indicating misleading paths near the start.",
            "suggestion": "Remove deceptive dead ends near the entry point and add visual cues to distinguish productive routes.",
            "expected_impact": "Lower confusion and faster completion times.",
            "priority": priority,
        })

    # --- Decision time (required field) ---
    if mean_decision is not None and (mean_decision > 5_000 or "mean_decision_time_ms" in top_names[:2]):
        priority = "high" if mean_decision > 10_000 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High decision time (avg {mean_decision/1000:.1f} s per action)",
            "technical_reason": "Players spend excessive time deciding each move, indicating cognitive overload or an unclear layout.",
            "suggestion": "Simplify the visible option space and reduce simultaneously visible branches.",
            "expected_impact": "Reduces cognitive load and shortens average decision time.",
            "priority": priority,
        })

    # --- Timeout rate (optional field) ---
    if mean_timeout is not None and (mean_timeout > 0.2 or "timeout_rate" in top_names[:2]):
        priority = "high" if mean_timeout > 0.4 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High timeout rate ({mean_timeout:.1%})",
            "technical_reason": "A significant share of actions end in timeout, suggesting the time limit is too tight.",
            "suggestion": "Increase the time limit or reduce the number of required steps to reach the goal.",
            "expected_impact": "Reduces time-pressure failures unrelated to player skill.",
            "priority": priority,
        })

    # --- Nodes expanded (optional field) ---
    if mean_nodes is not None and (mean_nodes > 500 or "mean_nodes_expanded" in top_names[:2]):
        priority = "high" if mean_nodes > 1_000 else "low"
        recs.append({
            "level_id": level_id,
            "problem": f"High search complexity (avg {mean_nodes:.0f} nodes expanded)",
            "technical_reason": "Large search space makes the level hard to navigate and expensive for AI agents.",
            "suggestion": "Constrain available moves or reduce the branching factor.",
            "expected_impact": "More approachable layout without removing core challenge.",
            "priority": priority,
        })

    # --- Retries (derived, always present) ---
    if mean_retries is not None and (mean_retries > 3 or "retry_count" in top_names[:2]):
        priority = "high" if mean_retries > 6 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High retry count (avg {mean_retries:.1f} restarts)",
            "technical_reason": "Repeated restarts indicate a punishing failure state or an invisible skill requirement.",
            "suggestion": "Show the failure reason on-screen and consider adding a mid-level checkpoint.",
            "expected_impact": "Converts frustrated quitters into persistent players.",
            "priority": priority,
        })

    if not recs:
        recs.append({
            "level_id": level_id,
            "problem": "No significant issues detected",
            "technical_reason": "All pathfinding metrics are within acceptable thresholds.",
            "suggestion": "Monitor player retention and revisit if engagement drops.",
            "expected_impact": "Maintains current performance.",
            "priority": "low",
        })

    return recs[:4]
