"""
families/puzzle_interaction/rules.py
Rule-based recommendations for the puzzle_interaction family.
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

    mean_decision       = _mean("mean_decision_time_ms")
    mean_wrong_rate     = _mean("wrong_interaction_rate")
    mean_hint_rate      = _mean("hint_rate")
    mean_retries        = _mean("retry_count")

    # --- Success rate (always available) ---
    if success_rate == 0.0:
        recs.append({
            "level_id": level_id,
            "problem": "No players solved this puzzle",
            "technical_reason": "Zero completions — the puzzle solution may be untriggerable or the win condition broken.",
            "suggestion": "Verify the completion trigger and walk through the solution manually. Consider adding a visible goal state.",
            "expected_impact": "Unblocks all players and reveals whether the puzzle is mechanically solvable.",
            "priority": "high",
        })
    elif success_rate < 0.3:
        recs.append({
            "level_id": level_id,
            "problem": f"Very low solve rate ({success_rate:.1%})",
            "technical_reason": "Fewer than 30% of sessions result in a solve. Puzzle logic may be too opaque.",
            "suggestion": "Add an ambient environmental hint or reduce the number of interactable red-herrings.",
            "expected_impact": "Raises solve rate toward the 40–65% target without removing the challenge.",
            "priority": "high",
        })
    elif success_rate > 0.9:
        recs.append({
            "level_id": level_id,
            "problem": f"Puzzle too straightforward ({success_rate:.1%} solve rate)",
            "technical_reason": "Very high solve rate with low wrong interactions suggests trivial difficulty.",
            "suggestion": "Add a secondary constraint or a misleading interactive element to increase puzzle depth.",
            "expected_impact": "Improves perceived puzzle quality and replayability.",
            "priority": "low",
        })

    # --- Wrong interaction rate (optional field) ---
    if mean_wrong_rate is not None and (mean_wrong_rate > 0.4 or "wrong_interaction_rate" in top_names[:2]):
        priority = "high" if mean_wrong_rate > 0.65 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High wrong interaction rate ({mean_wrong_rate:.1%})",
            "technical_reason": (
                "Players interact with the wrong objects more than they interact correctly, "
                "suggesting the puzzle's interactable elements are visually ambiguous."
            ),
            "suggestion": "Increase visual contrast between interactive and decorative objects. Add a subtle highlight or animation to key objects.",
            "expected_impact": "Reduces trial-and-error and makes puzzle intent clearer.",
            "priority": priority,
        })

    # --- Hint usage (optional field) ---
    if mean_hint_rate is not None and (mean_hint_rate > 0.15 or "hint_rate" in top_names[:2]):
        priority = "high" if mean_hint_rate > 0.35 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"Excessive hint usage (avg {mean_hint_rate:.1%} of actions are hint requests)",
            "technical_reason": (
                "High hint demand indicates the puzzle's logic is unclear without assistance. "
                "Players are solving via hint rather than deduction."
            ),
            "suggestion": "Embed the hint logic into the environment itself — use lighting, sound, or NPC dialogue to guide players passively.",
            "expected_impact": "Reduces hint dependency while preserving the feeling of discovery.",
            "priority": priority,
        })

    # --- Decision time (required field) ---
    if mean_decision is not None and (mean_decision > 6_000 or "mean_decision_time_ms" in top_names[:2]):
        priority = "high" if mean_decision > 12_000 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"Long deliberation time (avg {mean_decision/1000:.1f} s per action)",
            "technical_reason": "Players stall before each interaction, suggesting too many simultaneous options or unclear object affordances.",
            "suggestion": "Reduce the number of simultaneously visible interactables, or group related objects spatially.",
            "expected_impact": "Shortens decision time and reduces cognitive fatigue.",
            "priority": priority,
        })

    # --- Retries (derived, always present) ---
    if mean_retries is not None and (mean_retries > 3 or "retry_count" in top_names[:2]):
        priority = "high" if mean_retries > 6 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High retry count (avg {mean_retries:.1f} restarts)",
            "technical_reason": "Frequent restarts suggest players hit a dead state they cannot recover from without resetting.",
            "suggestion": "Allow partial undo or introduce a soft-reset that preserves discovered clues.",
            "expected_impact": "Reduces frustration and keeps players in the problem-solving mindset.",
            "priority": priority,
        })

    if not recs:
        recs.append({
            "level_id": level_id,
            "problem": "No significant issues detected",
            "technical_reason": "All puzzle interaction metrics are within acceptable thresholds.",
            "suggestion": "Consider adding an optional hard-mode variant to reward thorough exploration.",
            "expected_impact": "Increases replayability without affecting the base experience.",
            "priority": "low",
        })

    return recs[:4]
