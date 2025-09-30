from __future__ import annotations
import numpy as np
import pandas as pd
from .data import ensure_columns

def aggregate_sessions(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        raise ValueError("Cannot aggregate sessions from empty dataframe")

    base_cols = [
        "timestamp","session_id","player_id","level_id","event_type",
        "decision_time_ms","was_backtracked","success_flag","completion_time_ms",
    ]
    df = ensure_columns(df, base_cols)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for numcol in ["decision_time_ms","completion_time_ms","success_flag"]:
        if numcol in df.columns:
            df[numcol] = pd.to_numeric(df[numcol], errors="coerce")
    if "was_backtracked" in df.columns:
        df["was_backtracked"] = df["was_backtracked"].astype(str).str.lower().isin(["1","true","t","yes"]).astype(int)

    grouped = df.groupby(["session_id","player_id","level_id"], dropna=False)
    features = grouped.agg(
        session_time=("timestamp", lambda s: (s.max() - s.min()).total_seconds() if s.notna().any() else np.nan),
        attempt_count=("event_type", lambda s: (s == "level_start").sum()),
        action_count=("event_type", lambda s: (s == "action").sum()),
        mean_decision_time=("decision_time_ms", lambda s: np.nanmean(s.values) if np.isfinite(s.astype(float)).any() else np.nan),
        backtrack_ratio=("was_backtracked", lambda s: np.nanmean(s.values) if len(s) > 0 else np.nan),
        success_flag=("success_flag","max"),
        completion_time_ms=("completion_time_ms","max"),
    ).reset_index()

    for c in ["session_time","mean_decision_time","backtrack_ratio","completion_time_ms"]:
        if c in features.columns:
            features[c] = features[c].astype(float)
    features["action_count"] = features["action_count"].fillna(0).astype(int)
    features["attempt_count"] = features["attempt_count"].fillna(0).astype(int)
    features["completion_time_ms"] = features["completion_time_ms"].fillna(features["session_time"] * 1000)

    return features
