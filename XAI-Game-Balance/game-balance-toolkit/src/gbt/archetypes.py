from __future__ import annotations
from typing import List, Dict, Tuple
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

def cluster_archetypes(df_sessions: pd.DataFrame, n_clusters: int = 3) -> Tuple[pd.DataFrame, KMeans, List[str]]:
    behav_cols = [c for c in [
        "mean_decision_time","backtrack_ratio","action_count","attempt_count","session_time"
    ] if c in df_sessions.columns]

    if len(df_sessions) == 0:
        raise ValueError("Cannot cluster archetypes on empty dataframe")

    if len(df_sessions) < n_clusters:
        raise ValueError(f"Cannot create {n_clusters} clusters with only {len(df_sessions)} sessions")

    X = df_sessions[behav_cols].fillna(df_sessions[behav_cols].median())
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    df_sessions = df_sessions.copy()
    df_sessions["archetype"] = km.fit_predict(Xs)
    return df_sessions, km, behav_cols

def archetype_labels_from_centers(km: KMeans, behav_cols: List[str]) -> Dict[int, str]:
    centers = km.cluster_centers_
    names = {}
    for i, c in enumerate(centers):
        prof = dict(zip(behav_cols, c))
        # Note: centers are standardized (z-scores), so we compare relative to 0
        cautious = (prof.get("mean_decision_time", 0) > 0.3) and (prof.get("backtrack_ratio", 0) < -0.2)
        explorer = (prof.get("action_count", 0) > 0.3) and (prof.get("backtrack_ratio", 0) > 0.3)
        greedy = (prof.get("action_count", 0) > 0.3) and (prof.get("attempt_count", 0) < -0.2)
        if explorer:
            names[i] = "explorer"
        elif cautious:
            names[i] = "cautious"
        elif greedy:
            names[i] = "greedy"
        else:
            names[i] = "balanced"
    return names
