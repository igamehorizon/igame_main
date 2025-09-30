from __future__ import annotations
from typing import List, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

def train_success_model(df_sessions: pd.DataFrame) -> Tuple[GradientBoostingClassifier, List[str], float, pd.Series]:
    feat_cols = [c for c in [
        "session_time","attempt_count","action_count","mean_decision_time",
        "backtrack_ratio","completion_time_ms","player_elo","level_elo"
    ] if c in df_sessions.columns]

    df = df_sessions.dropna(subset=["success_flag"]).copy()

    if len(df) == 0:
        raise ValueError("No valid sessions with success_flag found for training")

    y = df["success_flag"].astype(int)

    if len(df) < 5:
        raise ValueError(f"Insufficient data for training: only {len(df)} sessions available (need at least 5)")

    strat = y if y.nunique() == 2 else None
    df_train, df_val = train_test_split(df, test_size=0.2, random_state=42, stratify=strat)

    # Compute medians from training set only to prevent data leakage
    train_medians = df_train[feat_cols].median()

    X_train = df_train[feat_cols].fillna(train_medians)
    X_val = df_val[feat_cols].fillna(train_medians)
    y_train = df_train["success_flag"].astype(int)
    y_val = df_val["success_flag"].astype(int)

    model = GradientBoostingClassifier(random_state=42)
    model.fit(X_train, y_train)
    try:
        val_proba = model.predict_proba(X_val)[:, 1]
        val_auc = roc_auc_score(y_val, val_proba)
    except Exception as e:
        print(f"Warning: Could not compute validation AUC: {e}")
        val_auc = float("nan")
    return model, feat_cols, val_auc, train_medians

def shap_global_importance(model: GradientBoostingClassifier, X: pd.DataFrame) -> dict:
    try:
        import shap  # type: ignore
    except ImportError:
        print("Warning: SHAP not installed, skipping feature importance calculation")
        return {}
    except Exception as e:
        print(f"Warning: Error importing SHAP: {e}")
        return {}

    try:
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(X)
        abs_mean = np.abs(sv).mean(axis=0)
        return {feat: float(w) for feat, w in zip(X.columns.tolist(), abs_mean)}
    except Exception as e:
        print(f"Warning: Could not compute SHAP values: {e}")
        return {}

def save_shap_summary_png(model: GradientBoostingClassifier, X: pd.DataFrame, path: str) -> None:
    try:
        import shap  # type: ignore
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: SHAP or matplotlib not installed, skipping SHAP plot generation")
        return
    except Exception as e:
        print(f"Warning: Error importing dependencies for SHAP plot: {e}")
        return

    try:
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(X)
        shap.summary_plot(sv, X, show=False)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
    except Exception as e:
        print(f"Warning: Could not generate SHAP summary plot: {e}")
