"""
shared/session_utils.py
Event conventions shared by all family extractors.

A session is: one or more level_start events, the player's action events, and an
end event (level_end / success_end / failure_end). Start and end events are markers:
they carry the outcome (success_flag, completion_time_ms) and general gameplay
variables, but they are not actions. Per-action metrics (averages, counts, rates)
are therefore computed over action events only.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

START_TYPES = {"level_start"}
END_TYPES = {"level_end", "success_end", "failure_end"}
MARKER_TYPES = START_TYPES | END_TYPES


def mask_markers(df: pd.DataFrame, per_action_cols: Iterable[str]) -> pd.DataFrame:
    """Flag action events and blank per-action fields on start/end markers, so that
    means, counts and rates only see real actions."""
    df["_is_action"] = ~df["event_type"].isin(MARKER_TYPES)
    for col in per_action_cols:
        if col in df.columns:
            df[col] = df[col].astype(float)
            df.loc[~df["_is_action"], col] = np.nan
    return df


def count_restarts(event_types: pd.Series) -> int:
    """Restarts = level_start events after the first one."""
    return max(int(event_types.isin(START_TYPES).sum()) - 1, 0)
