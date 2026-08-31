"""
families/pathfinding/extractor.py
Aggregates raw events into session-level features for the pathfinding family.

Required fields are coerced and kept; optional fields are coerced but left as
NaN when absent so rules can distinguish "not reported" from "zero".
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .config import FEATURE_COLS, OPTIONAL_DEFAULTS
from shared.generic_extractor import apply_generic_aggregations


def aggregate_sessions(events: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(events)

    # Required numeric fields — always present, coerce only
    for col in ["decision_time_ms", "completion_time_ms", "success_flag"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Optional fields — coerce to numeric; both absent columns and explicit null values
    # become NaN, which the rules engine treats as "not reported"
    for col in OPTIONAL_DEFAULTS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    # Treat success_end and failure_end as level_end equivalents
    END_TYPES = {"level_end", "success_end", "failure_end"}
    df["_is_end"] = df["event_type"].isin(END_TYPES)

    level_end = df[df["_is_end"]].copy()
    success_map = (
        level_end.sort_values("timestamp")
        .groupby(["session_id", "level_id"])["success_flag"]
        .last()
        .reset_index()
    ) if not level_end.empty else pd.DataFrame(
        columns=["session_id", "level_id", "success_flag"]
    )

    # retry_count: level_start events only
    START_TYPES = {"level_start"}

    grp = df.groupby(["session_id", "level_id", "player_id"])
    agg = grp.agg(
        n_actions             = ("event_type", "count"),
        mean_decision_time_ms = ("decision_time_ms", "mean"),
        completion_time_ms    = ("completion_time_ms", "max"),
        n_backtracks          = ("was_backtracked", "sum"),
        total_moves           = ("moves", "sum"),
        n_timeouts            = ("timeout_flag", "sum"),
        mean_nodes_expanded   = ("nodes_expanded", "mean"),
        retry_count           = ("event_type", lambda s: s.isin(START_TYPES).sum()),
        ts_min                = ("timestamp", "min"),
        ts_max                = ("timestamp", "max"),
        _has_backtrack        = ("was_backtracked", lambda s: s.notna().any()),
        _has_timeout          = ("timeout_flag", lambda s: s.notna().any()),
        _has_nodes            = ("nodes_expanded", lambda s: s.notna().any()),
        _has_moves            = ("moves", lambda s: s.notna().any()),
    ).reset_index()

    # Derived rates — only meaningful when source field was actually reported
    agg["backtrack_rate"] = np.where(
        agg["_has_backtrack"],
        agg["n_backtracks"] / agg["n_actions"].clip(lower=1),
        np.nan,
    )
    agg["timeout_rate"] = np.where(
        agg["_has_timeout"],
        agg["n_timeouts"] / agg["n_actions"].clip(lower=1),
        np.nan,
    )
    # Null out aggregates when the source field was never reported
    agg.loc[~agg["_has_nodes"], "mean_nodes_expanded"] = np.nan
    agg.loc[~agg["_has_moves"], "total_moves"] = np.nan

    agg["session_duration_ms"] = (
        (agg["ts_max"] - agg["ts_min"]).dt.total_seconds().fillna(0) * 1000
    )
    agg.drop(columns=["ts_min", "ts_max",
                       "_has_backtrack", "_has_timeout",
                       "_has_nodes", "_has_moves"], inplace=True)

    sessions = agg.merge(success_map, on=["session_id", "level_id"], how="left")
    sessions["success_flag"] = sessions["success_flag"].fillna(0).astype(int)

    # Only fill nulls for non-optional columns that must exist for the ML pipeline
    for col in ["n_actions", "mean_decision_time_ms", "completion_time_ms",
                "retry_count", "session_duration_ms"]:
        if col in sessions.columns:
            sessions[col] = sessions[col].fillna(0)

    sessions = apply_generic_aggregations(sessions, df)
    return sessions
