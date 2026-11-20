"""
analysis/recommend.py
Drives per-level rule generation and returns a flat recommendation list.

Order of execution per level:
  1. Family-specific rules  (high / medium / low)
  2. Generic gameplay variable rules (medium / low)
  3. Fallback if no recs at all

Archetype caveat: the level's per_archetype breakdown is passed to the
family rules, and to the generic rules only when no family rule fired,
so the descriptive cluster note appears at most once per level.
It never affects which rule fires or its priority (see shared/archetype_notes.py).

Final list is sorted: high → medium → low.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

import pandas as pd

from shared.generic_rules import generate_generic_recommendations


def build_recommendations(
    sessions_df: pd.DataFrame,
    per_level: Dict[str, Any],
    rules_fn: Callable,
) -> List[Dict[str, str]]:
    all_recs: List[Dict[str, str]] = []
    priority_order = {"high": 0, "medium": 1, "low": 2}

    for level_id, level_info in per_level.items():
        level_df      = sessions_df[sessions_df["level_id"] == level_id]
        success_rate  = level_info["success_rate"]
        top_features  = level_info.get("top_features", [])
        per_archetype = level_info.get("per_archetype")

        # 1. Family-specific rules
        family_recs = rules_fn(level_id, level_df, success_rate, top_features,
                               per_archetype=per_archetype)

        # 2. Generic gameplay variable rules (lower priority).
        #    Archetype note only if no family rule fired (avoids a duplicate caveat).
        generic_recs = generate_generic_recommendations(
            level_id, level_df, success_rate,
            per_archetype=None if family_recs else per_archetype,
        )

        all_recs.extend(family_recs)
        all_recs.extend(generic_recs)

    all_recs.sort(key=lambda r: priority_order.get(r.get("priority", "low"), 2))
    return all_recs
