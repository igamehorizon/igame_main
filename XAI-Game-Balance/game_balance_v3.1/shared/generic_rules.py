"""
shared/generic_rules.py
Generic gameplay variable recommendation engine.

Fires alongside family-specific rules but at lower priority (medium/low).
Rules are intentionally broad — these fields are semantically open and
shared across families. They help when a game has unusual mechanics or
when family rules do not fully explain an observed problem.

influence_score recommendations are deliberately conservative — the field
is too abstract for strong claims. Generic wording only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from shared.generic_fields import GENERIC_THRESHOLDS, INFLUENCE_SCORE_ENABLED


def generate_generic_recommendations(
    level_id: str,
    level_df: pd.DataFrame,
    success_rate: float,
) -> List[Dict[str, str]]:
    """
    Returns generic recommendations for a level based on the generic_* columns.
    All recommendations are priority "medium" or "low".
    Returns an empty list if no generic fields were reported.
    """
    recs: List[Dict[str, str]] = []

    def _mean(col: str) -> Optional[float]:
        full_col = f"generic_{col}"
        if full_col not in level_df.columns:
            return None
        val = level_df[full_col].mean()
        return None if (val is None or (isinstance(val, float) and np.isnan(val))) else float(val)

    def _reported(col: str) -> bool:
        full_col = f"generic_{col}"
        return full_col in level_df.columns and level_df[full_col].notna().any()

    t = GENERIC_THRESHOLDS

    # -----------------------------------------------------------------------
    # objective_progress
    # -----------------------------------------------------------------------
    if _reported("objective_progress"):
        mean_prog = _mean("objective_progress")
        if mean_prog is not None:
            if mean_prog < t["objective_progress_low"] and success_rate < 0.5:
                recs.append({
                    "level_id": level_id,
                    "problem": f"Players are not reaching the level objective "
                               f"(avg progress {mean_prog:.0%})",
                    "technical_reason": (
                        "Low objective_progress combined with a low success rate suggests "
                        "players are failing early rather than getting close and making mistakes. "
                        "The path to the objective may be unclear."
                    ),
                    "suggestion": (
                        "Add an early progress indicator or intermediate milestone "
                        "so players understand they are moving in the right direction."
                    ),
                    "expected_impact": "Earlier engagement with the core objective loop.",
                    "priority": "medium",
                })
            elif mean_prog > t["objective_progress_high"] and success_rate < 0.6:
                recs.append({
                    "level_id": level_id,
                    "problem": f"Players reach near-completion but still fail "
                               f"(avg progress {mean_prog:.0%}, pass rate {success_rate:.0%})",
                    "technical_reason": (
                        "High objective_progress with a moderate failure rate suggests a "
                        "late-level difficulty spike — players get close but are blocked at the end."
                    ),
                    "suggestion": (
                        "Review the final segment of the level for disproportionate difficulty. "
                        "Consider a checkpoint just before the final challenge."
                    ),
                    "expected_impact": "Converts near-misses into completions.",
                    "priority": "medium",
                })

    # -----------------------------------------------------------------------
    # system_state_score
    # -----------------------------------------------------------------------
    if _reported("system_state_score"):
        mean_state = _mean("system_state_score")
        if mean_state is not None and mean_state < t["system_state_score_low"]:
            recs.append({
                "level_id": level_id,
                "problem": f"Game world state is degrading significantly "
                           f"(avg system_state_score {mean_state:.2f})",
                "technical_reason": (
                    "A low system_state_score across sessions suggests players are leaving "
                    "the game world in a poor condition — resources depleted, structures "
                    "damaged, or systems destabilised beyond recovery."
                ),
                "suggestion": (
                    "Consider adding a recovery mechanism or reducing the rate at which "
                    "negative player actions degrade the game state."
                ),
                "expected_impact": "Players feel less locked into a deteriorating situation.",
                "priority": "medium",
            })

    # -----------------------------------------------------------------------
    # positive / negative action balance
    # -----------------------------------------------------------------------
    if _reported("positive_action_count") and _reported("negative_action_count"):
        mean_pos = _mean("positive_action_count") or 0.0
        mean_neg = _mean("negative_action_count") or 0.0
        total = mean_pos + mean_neg
        if total > 0:
            neg_ratio = mean_neg / total
            if neg_ratio > t["action_balance_ratio_high"]:
                recs.append({
                    "level_id": level_id,
                    "problem": f"Player actions are predominantly negative "
                               f"({neg_ratio:.0%} of tracked actions)",
                    "technical_reason": (
                        f"Players average {mean_neg:.1f} negative actions vs "
                        f"{mean_pos:.1f} positive actions per session. "
                        "This imbalance suggests the level is punishing players more "
                        "than it is rewarding progress."
                    ),
                    "suggestion": (
                        "Review whether negative outcomes are giving players enough feedback "
                        "to course-correct, or whether they are being penalised for "
                        "actions they had no reason to avoid."
                    ),
                    "expected_impact": "More balanced player experience with clearer cause and effect.",
                    "priority": "medium",
                })

    # -----------------------------------------------------------------------
    # custom_game_score
    # -----------------------------------------------------------------------
    if _reported("custom_game_score"):
        scores = level_df["generic_custom_game_score"].dropna()
        if len(scores) >= 2:
            low_threshold = float(scores.quantile(t["custom_game_score_low_pct"]))
            mean_score = float(scores.mean())
            score_std = float(scores.std())
            if score_std / (abs(mean_score) + 1e-6) > 0.5:
                recs.append({
                    "level_id": level_id,
                    "problem": f"High variance in custom game score "
                               f"(mean {mean_score:.1f}, std {score_std:.1f})",
                    "technical_reason": (
                        "Large spread in custom_game_score suggests very different player "
                        "experiences within the same level — some players scoring much higher "
                        "than others. This may indicate hidden skill gates or luck-based outcomes."
                    ),
                    "suggestion": (
                        "Investigate what separates high-scoring and low-scoring sessions. "
                        "If the gap is skill-based, consider adding a gentler progression curve. "
                        "If it is luck-based, reduce randomness in score-affecting events."
                    ),
                    "expected_impact": "More consistent player experience and perceived fairness.",
                    "priority": "low",
                })

    # -----------------------------------------------------------------------
    # influence_score — conservative, generic wording only
    # -----------------------------------------------------------------------
    if INFLUENCE_SCORE_ENABLED and _reported("influence_score"):
        mean_inf = _mean("influence_score")
        if mean_inf is not None and mean_inf < t["influence_score_low"]:
            recs.append({
                "level_id": level_id,
                "problem": f"Player influence on connected systems is low "
                           f"(avg influence_score {mean_inf:.2f})",
                "technical_reason": (
                    "A low influence_score suggests players are not meaningfully affecting "
                    "the system this score measures (e.g. NPC behaviour, environment, "
                    "faction standing). This may reduce perceived player agency."
                ),
                "suggestion": (
                    "Review whether player actions in this level have visible and timely "
                    "effects on the influence system. Add feedback to make the connection clearer."
                ),
                "expected_impact": "Players feel their actions matter beyond immediate outcomes.",
                "priority": "low",
            })

    return recs
