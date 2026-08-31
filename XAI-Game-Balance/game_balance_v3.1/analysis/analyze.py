"""
analysis/analyze.py
Core analysis pipeline: archetypes → prediction → XAI → per-level stats.
Mirrors V1's runner.py Steps C–F but returns a dict instead of writing to disk.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

N_ARCHETYPES = 3


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    sessions_df: pd.DataFrame,
    feature_cols: List[str],
    use_shap: bool = False,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Input : session-level DataFrame (one row per session×level)
    Output: analysis dict ready to be serialised into AnalyzeV2Response.analysis
    """
    warnings: List[str] = []
    n_sessions = len(sessions_df)

    # Clamp feature_cols to what is actually present
    feature_names = [c for c in feature_cols if c in sessions_df.columns]

    # Per-field coverage: fraction of sessions where the field was actually
    # reported (non-null). Used both for the existing "some fields missing"
    # warnings and for a stronger "field never once populated" signal, which
    # usually means the wrong Gameplay Data Type was selected or the field
    # was never wired up in the telemetry integration — a real data-quality
    # risk, distinct from a field being occasionally absent.
    feature_coverage: Dict[str, float] = {
        c: round(1.0 - float(sessions_df[c].isna().mean()), 4) if n_sessions else 0.0
        for c in feature_names
    }

    # Warn about family-specific optional fields that are missing
    nan_cols_family = [
        c for c in feature_names
        if sessions_df[c].isna().any() and not c.startswith("generic_")
    ]
    nan_cols_generic = [
        c for c in feature_names
        if sessions_df[c].isna().any() and c.startswith("generic_")
    ]
    if nan_cols_family:
        warnings.append(
            f"MISSING_OPTIONAL_FIELDS|"
            f"Some optional fields were not reported: {nan_cols_family}. "
            f"The ML pipeline has filled these with median values from the sessions that did report them. "
            f"Rules that depend on these fields are skipped — they will not fire incorrectly. "
            f"To get richer recommendations, add these fields to your event log. "
            f"If you are not tracking them intentionally, this warning can be ignored."
        )
    if nan_cols_generic:
        warnings.append(
            f"MISSING_GENERAL_FIELDS|"
            f"General gameplay variables were not reported: {[c.replace('generic_', '') for c in nan_cols_generic]}. "
            f"These are optional fields available for all gameplay types (objective_progress, system_state_score, etc.). "
            f"The ML pipeline has filled them with median values internally. "
            f"If you are not using general gameplay variables in your game, this warning can be safely ignored. "
            f"To use them, add the corresponding fields to your event JSON."
        )

    # Stronger warning: family-specific fields that are NEVER populated
    # (0% coverage), which is a much more concrete quality risk than
    # "occasionally missing" — likely wrong Gameplay Data Type or a
    # telemetry integration gap, not just an optional field being unused.
    never_populated_family = [
        c for c in nan_cols_family if feature_coverage.get(c, 0.0) == 0.0
    ]
    family_feature_names = [c for c in feature_names if not c.startswith("generic_")]
    overall_family_coverage = (
        round(sum(feature_coverage[c] for c in family_feature_names) / len(family_feature_names), 4)
        if family_feature_names else 1.0
    )
    # Not surfaced to the user in-app — this is evaluator-facing data only.
    # See telemetry_coverage.low_coverage_flag in the returned analysis dict,
    # and docs/evaluator_guide.md for how to use it.
    low_coverage_flag = bool(family_feature_names and overall_family_coverage < 0.4)
    if low_coverage_flag:
        warnings.append(
            f"LOW_TELEMETRY_COVERAGE|"
            f"Only {overall_family_coverage:.0%} of the expected optional fields for this "
            f"Gameplay Data Type were actually populated (never reported at all: "
            f"{never_populated_family or 'see per-field breakdown'}). "
            f"This usually means either the wrong Gameplay Data Type was selected for this game, "
            f"or the telemetry logging isn't sending these fields yet. "
            f"Recommendations for this session should be treated as low-confidence until this is fixed."
        )

    # --- Impute NaN for ML pipeline (median imputation on a copy) ---
    # Original sessions_df is preserved for the rules engine
    ml_df = sessions_df.copy()
    for col in feature_names:
        if col in ml_df.columns and ml_df[col].isna().any():
            median_val = ml_df[col].median()
            ml_df[col] = ml_df[col].fillna(median_val if not np.isnan(median_val) else 0)

    # --- Archetypes ---
    ml_df = _assign_archetypes(ml_df, feature_names, N_ARCHETYPES)
    # Copy archetype assignments back to original df
    sessions_df["archetype_id"] = ml_df["archetype_id"].values

    # --- ML prediction ---
    if n_sessions < 2:
        warnings.append(
            f"LOW_SESSION_COUNT|"
            f"Only 1 session was found in this upload. "
            f"The ML model requires at least 2 sessions to train — it has been skipped. "
            f"Feature importances are based on variance across fields rather than a trained model, "
            f"which is less reliable. "
            f"Recommendations may be limited or generic. "
            f"Upload more play sessions (ideally 10 or more) for meaningful analysis."
        )
        sessions_df["predicted_success_prob"] = float(sessions_df["success_flag"].mean())
        model = None
        importances, xai_method = _variance_importances(ml_df, feature_names, top_k)
    else:
        ml_df, model = _train_predict(ml_df, feature_names)
        sessions_df["predicted_success_prob"] = ml_df["predicted_success_prob"].values
        importances, xai_method = _compute_importances(
            model, ml_df, feature_names, use_shap, top_k
        )

    # --- Per-level stats ---
    per_level: Dict[str, Any] = {}
    levels_by_difficulty: List[Dict[str, Any]] = []

    for level_id, level_df in sessions_df.groupby("level_id"):
        sr = round(float(level_df["success_flag"].mean()), 4)
        mps = round(float(level_df["predicted_success_prob"].mean()), 4)

        per_archetype = []
        for arch_id, arch_df in level_df.groupby("archetype_id"):
            per_archetype.append({
                "archetype_id": int(arch_id),
                "n_sessions": int(len(arch_df)),
                "success_rate": round(float(arch_df["success_flag"].mean()), 4),
                "mean_predicted_success": round(float(arch_df["predicted_success_prob"].mean()), 4),
            })

        # Level-specific importances using imputed ml_df
        ml_level_df = ml_df[ml_df["level_id"] == level_id]
        if model is not None and len(ml_level_df) >= 2:
            level_imp, _ = _compute_importances(
                model, ml_level_df, feature_names, use_shap, top_k
            )
        else:
            level_imp = importances  # fallback to global

        per_level[str(level_id)] = {
            "level_id": str(level_id),
            "n_sessions": int(len(level_df)),
            "success_rate": sr,
            "mean_predicted_success": mps,
            "per_archetype": per_archetype,
            "top_features": level_imp,
        }
        levels_by_difficulty.append({"level_id": str(level_id), "success_rate": sr})

    levels_by_difficulty.sort(key=lambda x: x["success_rate"])

    # --- Per-agent summaries ---
    per_agent = _per_agent_summaries(sessions_df)

    return {
        "n_sessions": n_sessions,
        "n_levels": int(sessions_df["level_id"].nunique()),
        "n_agents": int(sessions_df["player_id"].nunique()),
        "overall_success_rate": round(float(sessions_df["success_flag"].mean()), 4),
        "levels_by_difficulty": levels_by_difficulty,
        "per_level": per_level,
        "per_agent": per_agent,
        "feature_importances": importances,
        "xai_method": xai_method,
        "telemetry_coverage": {
            "overall_family_coverage": overall_family_coverage,
            "per_field": feature_coverage,
            "low_coverage_flag": low_coverage_flag,
            "never_populated_fields": never_populated_family,
        },
        "warnings": warnings,
        "_sessions_df": sessions_df,  # passed through for rules; stripped before response
    }


# ---------------------------------------------------------------------------
# Archetypes
# ---------------------------------------------------------------------------

def _assign_archetypes(
    sessions_df: pd.DataFrame,
    feature_names: List[str],
    n: int,
) -> pd.DataFrame:
    player_features = (
        sessions_df.groupby("player_id")[feature_names].mean().reset_index()
    )
    X = player_features[feature_names].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    k = min(n, len(player_features))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
    player_features["archetype_id"] = kmeans.fit_predict(X_scaled)
    sessions_df = sessions_df.merge(
        player_features[["player_id", "archetype_id"]], on="player_id", how="left"
    )
    sessions_df["archetype_id"] = sessions_df["archetype_id"].fillna(0).astype(int)
    return sessions_df


# ---------------------------------------------------------------------------
# ML
# ---------------------------------------------------------------------------

def _train_predict(
    sessions_df: pd.DataFrame,
    feature_names: List[str],
) -> Tuple[pd.DataFrame, Any]:
    X = sessions_df[feature_names].values.astype(float)
    y = sessions_df["success_flag"].values.astype(int)

    if len(np.unique(y)) < 2:
        logger.warning("Single class in target — using dummy model.")
        sessions_df["predicted_success_prob"] = float(y.mean())
        return sessions_df, _DummyModel(feature_names)

    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
    )
    model.fit(X, y)
    sessions_df["predicted_success_prob"] = model.predict_proba(X)[:, 1]
    return sessions_df, model


class _DummyModel:
    def __init__(self, feature_names: List[str]):
        n = len(feature_names)
        self.feature_importances_ = np.ones(n) / n if n else np.array([])


# ---------------------------------------------------------------------------
# XAI
# ---------------------------------------------------------------------------

def _compute_importances(
    model: Any,
    sessions_df: pd.DataFrame,
    feature_names: List[str],
    use_shap: bool,
    top_k: int,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Self-contained XAI: SHAP TreeExplainer if available and requested,
    otherwise model.feature_importances_, otherwise variance heuristic.
    """
    # --- SHAP (optional) ---
    if use_shap:
        try:
            import shap as _shap
            X = sessions_df[feature_names].values.astype(float)
            explainer = _shap.TreeExplainer(model)
            sv = explainer.shap_values(X)
            if isinstance(sv, list):
                sv = sv[1]
            mean_abs = np.abs(sv).mean(axis=0)
            ranked = sorted(
                zip(feature_names, mean_abs), key=lambda x: x[1], reverse=True
            )[:top_k]
            result = [{"feature": f, "importance": round(float(v), 6)} for f, v in ranked]
            return result, "shap"
        except ImportError:
            logger.debug("SHAP not installed; falling back to feature_importances_.")
        except Exception as exc:
            logger.warning("SHAP failed (%s); falling back to feature_importances_.", exc)

    # --- feature_importances_ ---
    importances = getattr(model, "feature_importances_", None)
    if importances is not None:
        ranked = sorted(
            zip(feature_names, importances), key=lambda x: x[1], reverse=True
        )[:top_k]
        result = [{"feature": f, "importance": round(float(v), 6)} for f, v in ranked]
        return result, "feature_importances"

    # --- Variance heuristic (last resort) ---
    return _variance_importances(sessions_df, feature_names, top_k)


def _variance_importances(
    sessions_df: pd.DataFrame,
    feature_names: List[str],
    top_k: int,
) -> Tuple[List[Dict[str, Any]], str]:
    """Heuristic: rank features by variance (used when ML is skipped)."""
    variances = {col: float(sessions_df[col].var()) for col in feature_names if col in sessions_df.columns}
    total = sum(variances.values()) or 1.0
    ranked = sorted(variances.items(), key=lambda x: x[1], reverse=True)[:top_k]
    result = [{"feature": f, "importance": round(v / total, 6)} for f, v in ranked]
    return result, "variance_heuristic"


# ---------------------------------------------------------------------------
# Per-agent summaries
# ---------------------------------------------------------------------------

def _per_agent_summaries(sessions_df: pd.DataFrame) -> List[Dict[str, Any]]:
    summaries = []
    for player_id, pdf in sessions_df.groupby("player_id"):
        summaries.append({
            "player_id": str(player_id),
            "n_sessions": int(len(pdf)),
            "success_rate": round(float(pdf["success_flag"].mean()), 4),
            "mean_decision_time_ms": round(float(pdf["mean_decision_time_ms"].mean()), 2)
                if "mean_decision_time_ms" in pdf.columns else 0.0,
            "backtrack_rate": round(float(pdf["backtrack_rate"].mean()), 4)
                if "backtrack_rate" in pdf.columns else 0.0,
        })
    return summaries
