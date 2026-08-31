"""
families/accessibility_precision/rules.py
Rule-based recommendations for the Accessibility / Precision family.

Framing guidelines
------------------
- Use "may indicate" / "is associated with" rather than causal claims.
- Recommendations are directional but not absolute.
- Rules fire only when the relevant optional field was actually reported.
- All derived rates are event-normalised (per action, not per interaction).
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

    mean_error_rate      = _mean("error_rate")
    mean_assistance_rate = _mean("assistance_rate")
    mean_idle            = _mean("max_idle_time_ms")
    mean_precision       = _mean("mean_input_precision_score")
    mean_undo_rate       = _mean("undo_rate")
    mean_decision        = _mean("mean_decision_time_ms")
    mean_retries         = _mean("retry_count")

    # -----------------------------------------------------------------------
    # Success rate
    # -----------------------------------------------------------------------
    if success_rate == 0.0:
        recs.append({
            "level_id": level_id,
            "problem": "No players completed this task",
            "technical_reason": (
                "Zero completions may indicate a precision or interaction requirement "
                "that is too demanding for the current player group, or a broken "
                "completion trigger."
            ),
            "suggestion": (
                "Verify the completion trigger fires correctly. If intentional, "
                "consider reducing the minimum precision threshold or adding a "
                "guided first-attempt mode."
            ),
            "expected_impact": "Unlocks forward progress and reveals whether the barrier is technical or design-related.",
            "priority": "high",
        })
    elif success_rate < 0.3:
        recs.append({
            "level_id": level_id,
            "problem": f"Low completion rate ({success_rate:.1%})",
            "technical_reason": (
                f"Only {success_rate:.1%} of sessions result in completion. "
                "This may be associated with precision requirements or interaction "
                "patterns that create significant friction for players."
            ),
            "suggestion": (
                "Review whether the precision threshold or input model matches "
                "the expected player profile. Consider adding an adjustable "
                "difficulty or assistance option."
            ),
            "expected_impact": "Raises completion rate and reduces task abandonment.",
            "priority": "high",
        })
    elif success_rate > 0.92:
        recs.append({
            "level_id": level_id,
            "problem": f"Very high completion rate ({success_rate:.1%})",
            "technical_reason": (
                "Near-universal completion with low error and undo rates may indicate "
                "the task presents minimal precision challenge."
            ),
            "suggestion": (
                "If challenge is intended, consider raising the precision threshold "
                "or reducing assistance availability for experienced players."
            ),
            "expected_impact": "Better calibration between task difficulty and player skill.",
            "priority": "low",
        })

    # -----------------------------------------------------------------------
    # Error rate (event-normalised)
    # -----------------------------------------------------------------------
    if mean_error_rate is not None and (
        mean_error_rate > 0.3 or "error_rate" in top_names[:2]
    ):
        priority = "high" if mean_error_rate > 0.55 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High error rate ({mean_error_rate:.1%} of actions are errors)",
            "technical_reason": (
                f"An error rate of {mean_error_rate:.1%} per action is associated with "
                "frequent precision mistakes or unclear interaction targets. "
                "This may indicate the task's precision requirements exceed what players "
                "can reliably achieve, or that target areas are too small or ambiguous."
            ),
            "suggestion": (
                "Review interaction target sizes and visual clarity. "
                "Consider whether the precision threshold can be relaxed without "
                "removing the core challenge. A tolerance margin on accepted inputs "
                "may reduce friction significantly."
            ),
            "expected_impact": "Fewer frustrating failure moments and smoother task progression.",
            "priority": priority,
        })

    # -----------------------------------------------------------------------
    # Assistance rate (event-normalised)
    # -----------------------------------------------------------------------
    if mean_assistance_rate is not None and (
        mean_assistance_rate > 0.2 or "assistance_rate" in top_names[:2]
    ):
        priority = "high" if mean_assistance_rate > 0.45 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High assistance usage ({mean_assistance_rate:.1%} of actions use assistance)",
            "technical_reason": (
                f"An assistance rate of {mean_assistance_rate:.1%} per action may indicate "
                "players are relying on support features to complete the task rather than "
                "engaging with the core mechanic. This is associated with tasks where the "
                "base interaction is unclear or the precision requirement feels unreachable "
                "without aid."
            ),
            "suggestion": (
                "Review whether the task communicates its requirements clearly enough "
                "without assistance. If assistance is being used as a workaround, "
                "consider adjusting the base difficulty rather than relying on optional aids."
            ),
            "expected_impact": "More players engaging with the core mechanic rather than bypassing it.",
            "priority": priority,
        })

    # -----------------------------------------------------------------------
    # Idle time (longest inactivity period)
    # -----------------------------------------------------------------------
    if mean_idle is not None and (
        mean_idle > 8_000 or "max_idle_time_ms" in top_names[:2]
    ):
        priority = "high" if mean_idle > 20_000 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"Long idle periods (avg longest inactivity {mean_idle/1000:.1f} s)",
            "technical_reason": (
                f"An average longest idle period of {mean_idle/1000:.1f} s is associated with "
                "hesitation or uncertainty — players may be unsure what action to take next, "
                "or may be pausing before a demanding precision input."
            ),
            "suggestion": (
                "Review whether the task's next expected action is visually clear. "
                "A subtle prompt or animation after a period of inactivity may reduce "
                "hesitation without breaking immersion."
            ),
            "expected_impact": "Reduced hesitation and more confident player progression.",
            "priority": priority,
        })

    # -----------------------------------------------------------------------
    # Input precision score
    # -----------------------------------------------------------------------
    if mean_precision is not None and (
        mean_precision < 0.5 or "mean_input_precision_score" in top_names[:2]
    ):
        priority = "high" if mean_precision < 0.3 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"Low input precision score (avg {mean_precision:.2f} / 1.0)",
            "technical_reason": (
                f"An average precision score of {mean_precision:.2f} may indicate that "
                "the task's precision requirement is difficult to meet consistently. "
                "This is associated with inputs that demand fine motor control or timing "
                "that may not match the player group's capabilities or device."
            ),
            "suggestion": (
                "Consider whether the scoring threshold or accepted input range "
                "is appropriately calibrated. A wider acceptance zone or a "
                "progressive precision model (easier at start, stricter near completion) "
                "may reduce friction without removing the skill element."
            ),
            "expected_impact": "Higher average scores and lower abandonment on precision-heavy tasks.",
            "priority": priority,
        })

    # -----------------------------------------------------------------------
    # Undo rate (event-normalised)
    # -----------------------------------------------------------------------
    if mean_undo_rate is not None and (
        mean_undo_rate > 0.15 or "undo_rate" in top_names[:2]
    ):
        priority = "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High undo/correction rate ({mean_undo_rate:.1%} of actions are undos)",
            "technical_reason": (
                f"An undo rate of {mean_undo_rate:.1%} per action is associated with "
                "frequent corrections, which may indicate that players are not getting "
                "clear enough feedback before committing to an action, or that the "
                "action model makes it easy to place incorrectly."
            ),
            "suggestion": (
                "Review whether pre-commit feedback (previews, outlines, snap guides) "
                "is visible and timely. If players frequently undo shortly after acting, "
                "the action feedback may be arriving too late."
            ),
            "expected_impact": "Fewer correction loops and more deliberate, confident inputs.",
            "priority": priority,
        })

    # -----------------------------------------------------------------------
    # Decision time
    # -----------------------------------------------------------------------
    if mean_decision is not None and (
        mean_decision > 7_000 or "mean_decision_time_ms" in top_names[:2]
    ):
        priority = "high" if mean_decision > 15_000 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"Long decision time (avg {mean_decision/1000:.1f} s per action)",
            "technical_reason": (
                "High decision time per action in a precision context may indicate "
                "that players are carefully planning before each input due to fear of "
                "error, or that the task's requirements are not immediately legible."
            ),
            "suggestion": (
                "Review whether the task communicates what a correct action looks like "
                "before the player commits. Visual scaffolding or a preview mode may "
                "reduce pre-action anxiety and speed up decision-making."
            ),
            "expected_impact": "Faster, more confident inputs and reduced task fatigue.",
            "priority": priority,
        })

    # -----------------------------------------------------------------------
    # Retries
    # -----------------------------------------------------------------------
    if mean_retries is not None and (
        mean_retries > 3 or "retry_count" in top_names[:2]
    ):
        priority = "high" if mean_retries > 7 else "medium"
        recs.append({
            "level_id": level_id,
            "problem": f"High retry count (avg {mean_retries:.1f} restarts per session)",
            "technical_reason": (
                "Frequent restarts in a precision task context may indicate a "
                "punishing failure state — players are unable to recover from errors "
                "mid-task and must restart entirely."
            ),
            "suggestion": (
                "Consider whether partial recovery is possible — allowing players to "
                "correct errors without a full restart. A checkpoint or soft-reset that "
                "preserves partial progress may significantly reduce frustration."
            ),
            "expected_impact": "Fewer full restarts and a less punishing recovery experience.",
            "priority": priority,
        })

    if not recs:
        recs.append({
            "level_id": level_id,
            "problem": "No significant friction indicators detected",
            "technical_reason": "All Accessibility / Precision metrics are within acceptable thresholds.",
            "suggestion": (
                "Monitor for changes as the player group expands. "
                "Precision tasks can reveal friction at scale that small playtests miss."
            ),
            "expected_impact": "Maintains current performance.",
            "priority": "low",
        })

    return recs[:4]
