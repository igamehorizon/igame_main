from __future__ import annotations
import argparse
from pathlib import Path
import json
import pandas as pd

from .data import load_json_logs, generate_synthetic_logs
from .features import aggregate_sessions
from .elo import compute_elo
from .model import train_success_model, save_shap_summary_png
from .archetypes import cluster_archetypes, archetype_labels_from_centers
from .report import per_level_report

def main():
    parser = argparse.ArgumentParser(description="Game Balance Toolkit — V1")
    parser.add_argument("--input", required=True, help="Path to JSONL/JSON or 'SYNTH' for synthetic")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--clusters", type=int, default=3, help="Number of archetype clusters")
    parser.add_argument("--make-synth", action="store_true", help="Generate synthetic data if input is SYNTH")
    parser.add_argument("--players", type=int, default=40, help="#players for synthetic data")
    parser.add_argument("--levels", type=int, default=10, help="#levels for synthetic data")
    parser.add_argument("--sessions", type=int, default=1500, help="#sessions for synthetic data")

    args = parser.parse_args()

    # Validate arguments
    if args.clusters < 1:
        parser.error("--clusters must be at least 1")
    if args.players < 1:
        parser.error("--players must be at least 1")
    if args.levels < 1:
        parser.error("--levels must be at least 1")
    if args.sessions < 1:
        parser.error("--sessions must be at least 1")

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    # Load or synthesize events
    if args.make_synth and str(args.input).upper() == "SYNTH":
        df_events = generate_synthetic_logs(args.players, args.levels, args.sessions)
        synth_path = out / "synthetic_logs.jsonl"
        with open(synth_path, "w", encoding="utf-8") as fh:
            for _, row in df_events.iterrows():
                fh.write(json.dumps(row.to_dict()) + "\n")
    else:
        df_events = load_json_logs(args.input)

    # Aggregate to sessions
    df_sessions = aggregate_sessions(df_events)

    # Elo ratings
    p_elo, l_elo = compute_elo(df_sessions)
    df_sessions["player_elo"] = df_sessions["player_id"].astype(str).map(p_elo)
    df_sessions["level_elo"]  = df_sessions["level_id"].astype(str).map(l_elo)

    # Train success model
    model, feat_cols, val_auc, train_medians = train_success_model(df_sessions)

    # Cluster archetypes
    df_sessions, km, behav_cols = cluster_archetypes(df_sessions, n_clusters=args.clusters)
    arche_names = archetype_labels_from_centers(km, behav_cols)

    # Save summary
    summary = {
        "n_events": int(len(df_events)),
        "n_sessions": int(len(df_sessions)),
        "n_players": int(df_sessions["player_id"].nunique()),
        "n_levels": int(df_sessions["level_id"].nunique()),
        "val_auc_success": float(val_auc),
        "features_used": feat_cols,
        "archetype_names": arche_names,
    }
    with (out / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    # Per-level reports
    levels_dir = out / "levels"
    per_level_report(df_sessions, model, feat_cols, levels_dir, arche_names, train_medians)

    # Save session predictions (using training medians to prevent leakage)
    X = df_sessions[feat_cols].fillna(train_medians)
    if hasattr(model, "predict_proba"):
        df_sessions["pred_success"] = model.predict_proba(X)[:, 1]
    else:
        df_sessions["pred_success"] = model.predict(X)
    df_sessions.to_csv(out / "sessions_with_preds.csv", index=False)

    # SHAP global plot
    save_shap_summary_png(model, X, str(out / "shap_summary.png"))

    print(f"Done. Outputs in: {out}")

if __name__ == "__main__":
    main()
