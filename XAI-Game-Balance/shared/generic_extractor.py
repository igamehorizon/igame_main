"""
shared/generic_extractor.py
Aggregates generic gameplay variable columns from a raw event DataFrame.

Called at the end of every family extractor — after the family-specific
aggregation is complete — to append generic session-level columns.

Prefixes all output columns with "generic_" to avoid collisions with
family-specific columns (e.g. a family might also have a "moves" column).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from shared.generic_fields import (
    GENERIC_AGGREGATIONS,
    GENERIC_OPTIONAL_DEFAULTS,
    INFLUENCE_SCORE_ENABLED,
)


def apply_generic_aggregations(
    sessions: pd.DataFrame,
    raw_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Given:
      sessions  — the already-aggregated session DataFrame (one row per
                  session_id × level_id × player_id) produced by the
                  family extractor.
      raw_df    — the original flat event DataFrame before aggregation.

    Returns sessions with additional "generic_*" columns appended.
    Columns are NaN when the source field was absent or all-null.
    """
    fields_present = [
        f for f in GENERIC_OPTIONAL_DEFAULTS
        if f in raw_df.columns and raw_df[f].notna().any()
    ]

    if not fields_present:
        # No generic fields reported — add NaN columns so downstream
        # code never has to check for column existence
        for field in GENERIC_OPTIONAL_DEFAULTS:
            col = f"generic_{field}"
            if col not in sessions.columns:
                sessions[col] = np.nan
        return sessions

    # Coerce to numeric (nulls stay NaN)
    for field in fields_present:
        raw_df[field] = pd.to_numeric(raw_df[field], errors="coerce")

    # Build per-field aggregation dict
    agg_dict: dict = {}
    for field in fields_present:
        strategy = GENERIC_AGGREGATIONS.get(field, "last")
        if strategy == "last":
            # pandas groupby doesn't have a "last non-null" shortcut,
            # use lambda to get last non-null value
            agg_dict[field] = lambda s, f=field: s.dropna().iloc[-1] if s.notna().any() else np.nan
        else:
            agg_dict[field] = strategy  # "max", "sum", "mean"

    grp = raw_df.groupby(["session_id", "level_id", "player_id"])

    generic_agg = grp.agg(agg_dict).reset_index()

    # Rename to generic_ prefix
    rename_map = {f: f"generic_{f}" for f in fields_present}
    generic_agg.rename(columns=rename_map, inplace=True)

    # Merge into sessions
    merge_cols = ["session_id", "level_id", "player_id"]
    generic_cols = [f"generic_{f}" for f in fields_present]
    sessions = sessions.merge(
        generic_agg[merge_cols + generic_cols],
        on=merge_cols,
        how="left",
    )

    # Ensure all generic columns exist even if field wasn't in this upload
    for field in GENERIC_OPTIONAL_DEFAULTS:
        col = f"generic_{field}"
        if col not in sessions.columns:
            sessions[col] = np.nan

    # Conditionally include influence_score in feature cols
    if not INFLUENCE_SCORE_ENABLED:
        sessions["generic_influence_score"] = np.nan

    return sessions
