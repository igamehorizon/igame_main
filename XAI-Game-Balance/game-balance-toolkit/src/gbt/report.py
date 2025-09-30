from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from typing import Dict, List
from .model import shap_global_importance

def per_level_report(df_sessions: pd.DataFrame, model, feat_cols: List[str], out_dir: Path,
                     archetype_names: Dict[int, str], train_medians: pd.Series) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = df_sessions.copy()
    X = df[feat_cols].fillna(train_medians)
    if hasattr(model, "predict_proba"):
        df["pred_success"] = model.predict_proba(X)[:, 1]
    else:
        df["pred_success"] = model.predict(X)

    df["archetype_name"] = df["archetype"].map(archetype_names)

    global_feat = shap_global_importance(model, X)
    top_features = sorted(global_feat.items(), key=lambda kv: kv[1], reverse=True)[:8] if global_feat else []

    for level_id, g in df.groupby("level_id"):
        rep = {
            "level_id": str(level_id),
            "n_sessions": int(len(g)),
            "predicted_success_rate": float(np.nanmean(g["pred_success"])) if len(g) else None,
            "archetype_distribution": g["archetype_name"].value_counts(normalize=True).round(3).to_dict(),
            "top_features": top_features,
        }
        with (out_dir / f"level_{level_id}.json").open("w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2)
