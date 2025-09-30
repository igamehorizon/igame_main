# Game Balance Toolkit — Version 1

A small, game-agnostic AI + XAI pipeline for level balancing demos.
- Aggregates event logs to session features
- Estimates **player skill** and **level difficulty** (Elo-style)
- Trains a **success classifier** (GradientBoosting)
- Finds **player archetypes** (KMeans) with heuristic names
- Produces **per-level JSON** reports + **sessions CSV** with predicted success
- Optional: generate **synthetic data** for a self-contained demo

## Quickstart

### 1) Install
```bash
# Install in editable mode
pip install -e .
```

Or with a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 2) With your data
```bash
gbt --input data/logs.jsonl --output output/
```

### 3) Synthetic demo (no data required)
```bash
gbt --input SYNTH --output output/ --make-synth --players 50 --levels 12 --sessions 1000
```

### Outputs
- `output/summary.json`
- `output/levels/level_<ID>.json`
- `output/sessions_with_preds.csv`
- `output/shap_summary.png` (if SHAP is installed)

## Input format
JSON Lines (`.jsonl`) recommended (one event per line). Supported fields:
```
timestamp, session_id, player_id, level_id, event_type  # {level_start, action, level_end}
decision_time_ms, was_backtracked, success_flag (on level_end), completion_time_ms (optional)
```
The loader is forgiving and will fill missing columns where possible.


## Streamlit Viewer

After running the CLI and generating results:

```bash
streamlit run apps/streamlit_app.py
```

If your results are in a non-default folder:
- Set the **Results folder** text box at the top of the app (e.g., `output`).

## Example datasets

- `examples/tiny_showcase.jsonl` — Small hand-crafted dataset (6 sessions across 2 levels).
- `examples/synth_demo.jsonl` — Medium synthetic dataset (~1000 sessions, 50 players, 12 levels).

### Try them
```bash
# Tiny set
gbt --input examples/tiny_showcase.jsonl --output output_tiny/

# Medium synthetic
gbt --input examples/synth_demo.jsonl --output output_synth/
```

Then open the Streamlit viewer:
```bash
streamlit run apps/streamlit_app.py
# Set Results folder to output_tiny or output_synth
```
