# Game Balance Tool — v3.1

A researcher-facing application for analysing gameplay telemetry and generating
prioritised design recommendations. Built for the i-Game ecosystem (Horizon Europe, WP4 / Task 4.2).

The tool accepts real or synthetic gameplay data, runs an ML + XAI pipeline
(KMeans archetypes, Gradient Boosting, SHAP), and guides designers through a
structured iterative balancing workflow — from baseline upload through recommendations
to follow-up comparison.

---

## Setup & Run

### Step 1 — Create the virtual environment

**Windows — Command Prompt**
```cmd
python -m venv .venv31
.venv31\Scripts\activate.bat
```

**Windows — PowerShell**
```powershell
python -m venv .venv31
.venv31\Scripts\Activate.ps1
```

> **PowerShell note:** if you get an execution policy error, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**macOS / Linux**
```bash
python3 -m venv .venv31
source .venv31/bin/activate
```

---

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 3 — Start the API

Open a terminal in the **project root** with the environment activated:

```bash
python run.py
```

---

### Step 4 — Start the Streamlit UI

Open a **second terminal** in the **project root** with the environment activated:

```bash
streamlit run app/streamlit_app.py
```

UI opens at: `http://160.40.54.131:8501/`

---

### Deactivating the environment

```bash
deactivate
```

---

## Workflow

The UI is divided into six sections:

| Section | Purpose |
|---------|---------|
| **01 // GAMEPLAY INSTANCE** | Enter game name, select Gameplay Data Type, describe the gameplay section |
| **02 // TELEMETRY SCHEMA** | Reference for required and optional fields; download JSON template |
| **03 // UPLOAD & ANALYZE** | Upload telemetry file and run the analysis pipeline |
| **04 // RESULTS** | Baseline analysis — overview, difficulty ranking, per-player breakdown, prioritised recommendations |
| **05 // COMPARE AFTER CHANGES** | Upload follow-up data; comparison dashboard (Resolved / Persisting / New) |
| **06 // LEAVE A REVIEW** | Participant feedback form |

---

## Gameplay Data Types

Five domain-specific types are supported. Each determines which optional fields
are suggested and which recommendation rules apply:

| Type | Key optional fields |
|------|-------------------|
| **Generic** | None — base fields only |
| **Pathfinding / Navigation** | `was_backtracked`, `moves`, `timeout_flag`, `nodes_expanded` |
| **Puzzle / Interaction** | `interaction_count`, `wrong_interaction_count`, `hint_count` |
| **Strategy / Combat** | `moves`, `damage_taken`, `deaths`, `resource_loss`, `healing_usage` |
| **Accessibility / Precision** | `error_count`, `assistance_used`, `idle_time_ms`, `input_precision_score`, `undo_count` |

General Gameplay Variables (`objective_progress`, `system_state_score`,
`positive_action_count`, `negative_action_count`, `influence_score`,
`custom_game_score`) are available as optional fields for all types.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analyze` | Upload telemetry; run full pipeline; return analysis + recommendations |
| `POST` | `/session/{id}/iteration` | Upload follow-up data for an existing balancing session |
| `POST` | `/session/{id}/applied` | Record which recommendations were applied before follow-up |
| `GET`  | `/families` | List registered Gameplay Data Types |
| `GET`  | `/health` | Health check |
| `GET`  | `/docs` | Interactive Swagger UI |

### Request format (`POST /analyze`)

```json
{
  "gameplay_instance": {
    "instance_id": "ant_colony_001",
    "start_condition": "agent enters the maze",
    "end_condition": "agent reaches exit or time expires",
    "success_condition": "agent reaches exit",
    "failure_condition": "agent times out or gets stuck",
    "telemetry_family": "pathfinding"
  },
  "events": [ ... ]
}
```

### Response format

```json
{
  "status": "ok",
  "family": "pathfinding",
  "session_id": "ant_colony_001_080726_143522",
  "analysis": {
    "n_sessions": 10,
    "n_levels": 1,
    "n_agents": 4,
    "overall_success_rate": 0.3,
    "levels_by_difficulty": [...],
    "per_level": {...},
    "per_agent": [...],
    "feature_importances": [...],
    "xai_method": "feature_importances",
    "warnings": []
  },
  "recommendations": [
    {
      "level_id": "maze_level_1",
      "problem": "High backtrack rate (52.3%)",
      "technical_reason": "Players frequently reverse direction, indicating misleading paths near the start.",
      "suggestion": "Remove deceptive dead ends near the entry point and add visual cues.",
      "expected_impact": "Lower confusion and faster completion times.",
      "priority": "high"
    }
  ],
  "errors": []
}
```

---


---

## Local Persistence

All session data is saved automatically — nothing is lost between runs.

```
data/balancing_sessions/session_{game}_{counter}_{DDMMYY}_{HHMMSS}/
    metadata.json                   session info, iteration list, original filenames
    iteration_01_upload.json        baseline telemetry
    iteration_01_result.json        baseline analysis result
    iteration_02_applied_recs.json  recommendations marked as applied
    iteration_02_upload.json        follow-up telemetry
    iteration_02_result.json        follow-up analysis result
```

---

## How to Add a New Gameplay Data Type

1. Create `families/<your_type>/config.py` — define `REQUIRED_FIELDS`, `OPTIONAL_DEFAULTS`, `FEATURE_COLS`
2. Create `families/<your_type>/extractor.py` — implement `aggregate_sessions(events) -> pd.DataFrame`
3. Create `families/<your_type>/rules.py` — implement `generate_recommendations(level_id, level_df, success_rate, top_features) -> List[dict]`
4. Register in `core/registry.py` via `register_family(...)`
5. Add the display name to `FAMILY_DISPLAY_NAMES` in `app/streamlit_app.py`

No other files need to change.

---

## XAI — SHAP vs Built-in Feature Importances

By default, feature importances use the GBM model's built-in `feature_importances_`.
SHAP is installed and available. To enable it, pass `use_shap=True` to `run_pipeline()`
in `api/main.py`. No other changes needed — the XAI layer detects SHAP automatically.

---

## Notes

- **Null vs 0**: omitting a field or sending `null` means "not collected". `0` means a genuine zero value. This distinction drives populated-field detection and ML pipeline inclusion.
- **ML requires ≥ 2 sessions**: with only 1 session the GBM model is skipped and variance-based heuristics are used instead. A warning is shown in the UI.
- **Derived columns** (e.g. `backtrack_rate`) must appear in the validator's `populated_fields` set or they will be silently excluded from analysis.
- **Session ID format**: `{game_name}_{counter}_{DDMMYY}_{HHMMSS}` — e.g. `ant_colony_002_080726_160011`.