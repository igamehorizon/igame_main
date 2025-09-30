
import json
import os
from pathlib import Path

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Game Balance Toolkit — Viewer", layout="wide")

st.title("Game Balance Toolkit — Viewer (V1)")

st.markdown("""
Use this app to explore your **Version 1** results: success predictions, archetype mix,
and key drivers (SHAP). Point it at the `--output` folder produced by the CLI.
""")

results_dir = st.text_input("Results folder", value="output")
results_path = Path(results_dir)

if not results_path.exists():
    st.warning("Results folder not found. Run the CLI first or correct the path.")
    st.stop()

summary_path = results_path / "summary.json"
sessions_path = results_path / "sessions_with_preds.csv"
levels_dir = results_path / "levels"
shap_img_path = results_path / "shap_summary.png"

# Load data
if not summary_path.exists() or not sessions_path.exists() or not levels_dir.exists():
    st.warning("Missing expected files. Ensure summary.json, sessions_with_preds.csv, and levels/ exist.")
    st.stop()

summary = json.loads(summary_path.read_text(encoding="utf-8"))
sessions = pd.read_csv(sessions_path)
level_files = sorted([p for p in levels_dir.glob("level_*.json")])
levels = [json.loads(p.read_text(encoding="utf-8")) for p in level_files]
levels_df = pd.DataFrame(levels)

# --- Sidebar filters
with st.sidebar:
    st.header("Filters")
    level_ids = levels_df["level_id"].astype(str).tolist() if len(levels_df) else []
    level_choice = st.selectbox("Level", options=["(All)"] + level_ids, index=0)
    arche_opts = sorted(list(sessions.get("archetype", pd.Series(dtype=int)).unique()))
    arche_filter = st.multiselect("Archetype (cluster id)", options=[int(a) for a in arche_opts if pd.notna(a)], default=[])
    proba_min, proba_max = st.slider("Predicted success range", 0.0, 1.0, (0.0, 1.0))

# Filter sessions
df = sessions.copy()
if level_choice != "(All)":
    df = df[df["level_id"].astype(str) == str(level_choice)]
if len(arche_filter) > 0:
    df = df[df["archetype"].isin(arche_filter)]
df = df[(df["pred_success"] >= proba_min) & (df["pred_success"] <= proba_max)]

# --- Top-level metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Sessions", f"{len(df):,}")
c2.metric("Players", f"{df['player_id'].nunique():,}")
c3.metric("Levels", f"{df['level_id'].nunique():,}")
c4.metric("Val AUC (success)", f"{summary.get('val_auc_success', float('nan')):.3f}" if not pd.isna(summary.get('val_auc_success', np.nan)) else "n/a")

st.divider()

# --- Predicted success by level
st.subheader("Predicted Success Rate by Level")
fig1, ax1 = plt.subplots()
plot_df = df.groupby("level_id")["pred_success"].mean().sort_values(ascending=False).reset_index()
if len(plot_df):
    labels = plot_df["level_id"].astype(str).tolist()
    ax1.bar(range(len(labels)), plot_df["pred_success"])
    ax1.set_xlabel("Level")
    ax1.set_ylabel("Predicted success rate")
    ax1.set_ylim(0, 1)
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=45, ha="right")
    st.pyplot(fig1)
else:
    st.info("No data to plot.")

# --- Archetype distribution (sessions-weighted) for selection
st.subheader("Archetype Distribution")
fig2, ax2 = plt.subplots()
arch_counts = df["archetype"].value_counts(normalize=True).sort_index()
if len(arch_counts):
    ax2.bar(arch_counts.index.astype(str), arch_counts.values)
    ax2.set_xlabel("Archetype (cluster id)")
    ax2.set_ylabel("Share of sessions")
    st.pyplot(fig2)
else:
    st.info("No archetype data to plot.")

# --- Feature influences (from per-level reports top_features, aggregated)
st.subheader("Top Features (from SHAP global importances)")
all_feats = []
for rep in levels:
    for feat, weight in rep.get("top_features", []):
        all_feats.append((feat, weight))
agg = {}
for feat, w in all_feats:
    agg[feat] = agg.get(feat, 0.0) + float(w)
feat_df = pd.DataFrame([{"feature": k, "weight": v} for k, v in agg.items()]).sort_values("weight", ascending=False)
fig3, ax3 = plt.subplots()
if len(feat_df):
    ax3.barh(feat_df["feature"].iloc[:12][::-1], feat_df["weight"].iloc[:12][::-1])
    ax3.set_xlabel("Aggregate SHAP (abs mean)")
    st.pyplot(fig3)
else:
    st.info("No SHAP features found. Install SHAP and rerun the CLI to generate them.")

# --- SHAP summary image
if shap_img_path.exists():
    st.subheader("Global SHAP Summary")
    st.image(str(shap_img_path), caption="shap_summary.png")

# --- Detail table
st.subheader("Session Details")
st.dataframe(df.head(1000), use_container_width=True)
