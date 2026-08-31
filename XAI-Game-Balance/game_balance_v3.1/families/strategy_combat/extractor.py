"""
families/strategy_combat/extractor.py
Aggregates raw events into session-level features for the strategy_combat family.

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

    # Required numeric fields
    for col in ["decision_time_ms", "completion_time_ms", "success_flag"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Optional fields — preserve NaN when absent
    for col in OPTIONAL_DEFAULTS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    END_TYPES = {"level_end", "success_end", "failure_end"}
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
        n_actions            = ("event_type", "count"),
        mean_decision_time_ms= ("decision_time_ms", "mean"),
        completion_time_ms   = ("completion_time_ms", "max"),
        total_moves          = ("moves", "sum"),
        total_damage_taken   = ("damage_taken", "sum"),
        total_deaths         = ("deaths", "sum"),
        total_resource_loss  = ("resource_loss", "sum"),
        total_healing_usage  = ("healing_usage", "sum"),
        retry_count          = ("event_type", lambda s: s.isin({"level_start"}).sum()),
        ts_min               = ("timestamp", "min"),
        ts_max               = ("timestamp", "max"),
        _has_moves           = ("moves", lambda s: s.notna().any()),
        _has_damage          = ("damage_taken", lambda s: s.notna().any()),
        _has_deaths          = ("deaths", lambda s: s.notna().any()),
        _has_resource        = ("resource_loss", lambda s: s.notna().any()),
        _has_healing         = ("healing_usage", lambda s: s.notna().any()),
    ).reset_index()

    # Derived ratios — only when both sources were reported
    agg["damage_per_move"] = np.where(
        agg["_has_damage"] & agg["_has_moves"],
        agg["total_damage_taken"] / agg["total_moves"].clip(lower=1),
        np.nan,
    )
    agg["healing_to_damage_ratio"] = np.where(
        agg["_has_healing"] & agg["_has_damage"],
        agg["total_healing_usage"] / agg["total_damage_taken"].clip(lower=1),
        np.nan,
    )

    # Null out aggregates when source was never reported
    for col, flag in [
        ("total_moves",         "_has_moves"),
        ("total_damage_taken",  "_has_damage"),
        ("total_deaths",        "_has_deaths"),
        ("total_resource_loss", "_has_resource"),
        ("total_healing_usage", "_has_healing"),
    ]:
        agg.loc[~agg[flag], col] = np.nan

    agg["session_duration_ms"] = (
        (agg["ts_max"] - agg["ts_min"]).dt.total_seconds().fillna(0) * 1000
    )
    agg.drop(columns=["ts_min", "ts_max",
                       "_has_moves", "_has_damage", "_has_deaths",
                       "_has_resource", "_has_healing"], inplace=True)

    sessions = agg.merge(success_map, on=["session_id", "level_id"], how="left")
    sessions["success_flag"] = sessions["success_flag"].fillna(0).astype(int)

    for col in ["n_actions", "mean_decision_time_ms", "completion_time_ms",
                "retry_count", "session_duration_ms"]:
        if col in sessions.columns:
            sessions[col] = sessions[col].fillna(0)

    sessions = apply_generic_aggregations(sessions, df)
    return sessions
