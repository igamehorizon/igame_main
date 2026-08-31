"""
families/accessibility_precision/extractor.py
Aggregates raw events into session-level features for the
Accessibility / Precision telemetry family.

Aggregation strategies per field
---------------------------------
- error_count           → sum
- assistance_used       → sum
- idle_time_ms          → max  (longest inactivity period)
- input_precision_score → mean (average precision across actions)
- undo_count            → sum

Derived rates (event-normalised, not interaction-normalised)
-------------------------------------------------------------
- error_rate        = total_errors / n_actions
- assistance_rate   = total_assistance / n_actions
- undo_rate         = total_undos / n_actions

All rates are null when n_actions == 0 or the source field was not reported.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .config import FEATURE_COLS, OPTIONAL_DEFAULTS
from shared.generic_extractor import apply_generic_aggregations

END_TYPES   = {"level_end", "success_end", "failure_end"}
START_TYPES = {"level_start"}


def aggregate_sessions(events: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(events)

    # Required numeric fields
    for col in ["decision_time_ms", "completion_time_ms", "success_flag"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Optional fields — coerce to numeric; both absent columns and explicit
    # null values become NaN, treated as "not reported" by the rules engine
    for col in OPTIONAL_DEFAULTS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    # Success: last end event per session × level
    level_end = df[df["event_type"].isin(END_TYPES)].copy()
    success_map = (
        level_end.sort_values("timestamp")
        .groupby(["session_id", "level_id"])["success_flag"]
        .last()
        .reset_index()
    ) if not level_end.empty else pd.DataFrame(
        columns=["session_id", "level_id", "success_flag"]
    )

    grp = df.groupby(["session_id", "level_id", "player_id"])

    agg = grp.agg(
        n_actions               = ("event_type", "count"),
        mean_decision_time_ms   = ("decision_time_ms", "mean"),
        completion_time_ms      = ("completion_time_ms", "max"),
        total_errors            = ("error_count", "sum"),
        total_assistance        = ("assistance_used", "sum"),
        max_idle_time_ms        = ("idle_time_ms", "max"),
        mean_input_precision_score = ("input_precision_score", "mean"),
        total_undos             = ("undo_count", "sum"),
        retry_count             = ("event_type", lambda s: s.isin(START_TYPES).sum()),
        ts_min                  = ("timestamp", "min"),
        ts_max                  = ("timestamp", "max"),
        # Presence flags — used to null out aggregates when source not reported
        _has_errors             = ("error_count", lambda s: s.notna().any()),
        _has_assistance         = ("assistance_used", lambda s: s.notna().any()),
        _has_idle               = ("idle_time_ms", lambda s: s.notna().any()),
        _has_precision          = ("input_precision_score", lambda s: s.notna().any()),
        _has_undos              = ("undo_count", lambda s: s.notna().any()),
    ).reset_index()

    # Null out aggregates when source field was never reported
    for col, flag in [
        ("total_errors",               "_has_errors"),
        ("total_assistance",           "_has_assistance"),
        ("max_idle_time_ms",           "_has_idle"),
        ("mean_input_precision_score", "_has_precision"),
        ("total_undos",                "_has_undos"),
    ]:
        agg.loc[~agg[flag], col] = np.nan

    # Derived event-normalised rates — only when source was reported and n_actions > 0
    def _rate(total_col, flag_col) -> pd.Series:
        return np.where(
            agg[flag_col] & (agg["n_actions"] > 0),
            agg[total_col] / agg["n_actions"],
            np.nan,
        )

    agg["error_rate"]      = _rate("total_errors",      "_has_errors")
    agg["assistance_rate"] = _rate("total_assistance",  "_has_assistance")
    agg["undo_rate"]       = _rate("total_undos",       "_has_undos")

    agg["session_duration_ms"] = (
        (agg["ts_max"] - agg["ts_min"]).dt.total_seconds().fillna(0) * 1000
    )
    agg.drop(columns=[
        "ts_min", "ts_max",
        "_has_errors", "_has_assistance", "_has_idle",
        "_has_precision", "_has_undos",
    ], inplace=True)

    sessions = agg.merge(success_map, on=["session_id", "level_id"], how="left")
    sessions["success_flag"] = sessions["success_flag"].fillna(0).astype(int)

    # Fill only always-present columns
    for col in ["n_actions", "mean_decision_time_ms", "completion_time_ms",
                "retry_count", "session_duration_ms"]:
        if col in sessions.columns:
            sessions[col] = sessions[col].fillna(0)

    sessions = apply_generic_aggregations(sessions, df)
    return sessions
