"""
families/game_jam_generic/extractor.py
Aggregates raw events into session-level features for game_jam_generic.

Derives everything from the 8 base required fields — no optional columns.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .config import FEATURE_COLS
from shared.generic_extractor import apply_generic_aggregations


def aggregate_sessions(events: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(events)

    for col in ["decision_time_ms", "completion_time_ms", "success_flag"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    # Success: last level_end per session×level
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
        n_actions             = ("event_type", "count"),
        mean_decision_time_ms = ("decision_time_ms", "mean"),
        completion_time_ms    = ("completion_time_ms", "max"),
        retry_count           = ("event_type", lambda s: s.isin({"level_start"}).sum()),
        ts_min                = ("timestamp", "min"),
        ts_max                = ("timestamp", "max"),
        n_successes           = ("success_flag", "sum"),
    ).reset_index()

    agg["session_duration_ms"] = (
        (agg["ts_max"] - agg["ts_min"]).dt.total_seconds().fillna(0) * 1000
    )
    agg["success_rate_within_session"] = (
        agg["n_successes"] / agg["n_actions"].clip(lower=1)
    )
    agg.drop(columns=["ts_min", "ts_max", "n_successes"], inplace=True)

    sessions = agg.merge(success_map, on=["session_id", "level_id"], how="left")
    sessions["success_flag"] = sessions["success_flag"].fillna(0).astype(int)

    for col in FEATURE_COLS:
        if col in sessions.columns:
            sessions[col] = sessions[col].fillna(0)

    sessions = apply_generic_aggregations(sessions, df)
    return sessions
