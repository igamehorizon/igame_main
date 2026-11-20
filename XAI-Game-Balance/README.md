# i-Game Game Balance Tool

The Game Balance Tool analyses gameplay data from your game and tells you which levels are too hard or too easy, why, and what to change first. It combines machine learning with explainable AI (SHAP), so every recommendation comes with the reason behind it.

You can also run a **balancing loop**: analyse your game, apply some of the recommendations, collect new gameplay data, and compare the two versions to see which problems were resolved, which persist, and which are new.

Everything runs on your own computer. Your data is not sent anywhere.

---

## Quick start

### 1. Install Python (once)

You need **Python 3.10 or newer**.

- **Windows:** download it from [python.org/downloads](https://www.python.org/downloads/). During installation, tick **"Add python.exe to PATH"**.
- **macOS:** download it from [python.org/downloads](https://www.python.org/downloads/).
- **Linux:** usually already installed. On Debian/Ubuntu you may also need: `sudo apt install python3-venv`

### 2. Download and unzip

Download the latest zip from the [Releases page](https://github.com/igamehorizon/igame_main/releases) and unzip it somewhere with a short path, such as your Desktop or `C:\igame-game-balance-tool`.

**Windows:** right-click the zip and choose **Extract All…**, then open the extracted folder. Do not run the START file from inside the zip.

### 3. Start the tool

| System | How to start |
|---|---|
| **Windows** | Double-click **`START (Windows).bat`**. The first time, Windows may show *"Windows protected your PC"*: click **More info**, then **Run anyway**. |
| **macOS** | Double-click **`START (macOS).command`**. The first time, macOS may block it: right-click the file, choose **Open**, then **Open** again. |
| **Linux** | Open a terminal in the folder and run `./start-linux.sh` |

The **first start** sets everything up and takes a few minutes (it needs an internet connection). After that, the tool starts in a few seconds.

The tool opens in your browser at **http://localhost:8501**. Keep the black window open while you work; **close it to stop the tool**.

---

## How to use it

The interface guides you through five steps:

| Section | What you do |
|---|---|
| **01 // Gameplay instance** | Name your game, choose the gameplay data type, and describe the part of the game you are testing (start, end, success and failure conditions). |
| **02 // Telemetry schema** | See which fields to record and download a ready-made JSON template. |
| **03 // Upload & analyze** | Upload the gameplay data you collected and run the analysis. |
| **04 // Results** | See the difficulty ranking, player breakdown and prioritised recommendations, each with its explanation. Tick the recommendations you decide to apply. |
| **05 // Compare after changes** | Upload data from your updated game and see what was resolved, what persists and what is new. |

**Just want to try it?** The `examples` folder contains ready-to-use files:

- `pathfinding_baseline.json`: upload this in Section 03 (gameplay data type: Pathfinding / Navigation).
- `pathfinding_followup.json`: upload this in Section 05 to see the comparison.
- `showcase_accessibility_precision.json`: an Accessibility / Precision example.

### Gameplay data types

Choose the type that best matches the part of your game you are testing. It decides which extra fields are suggested and which design rules apply.

| Type | Typical extra fields |
|---|---|
| **Generic** (any game) | none: base fields only |
| **Pathfinding / Navigation** | `was_backtracked`, `moves`, `timeout_flag`, `nodes_expanded` |
| **Puzzle / Interaction** | `interaction_count`, `wrong_interaction_count`, `hint_count` |
| **Strategy / Combat** | `moves`, `damage_taken`, `deaths`, `resource_loss`, `healing_usage` |
| **Accessibility / Precision** | `error_count`, `assistance_used`, `idle_time_ms`, `input_precision_score`, `undo_count` |

General gameplay variables (`objective_progress`, `system_state_score`, `positive_action_count`, `negative_action_count`, `influence_score`, `custom_game_score`) can be added to any type.

**Tips for good results**

- Each play session is a `level_start` event, one event per player action (`event_type: "action"`), and an end event (`level_end`). Record per-action fields (decision time, errors, backtracks, …) on the action events; the start and end events carry the outcome (`success_flag`, `completion_time_ms`). Per-action fields on start/end events are ignored.
- A restart is an extra `level_start` event in the same session.
- If you did not record a value, send `null` (or leave the field out). Send `0` only when the value really was zero.
- `success_flag` and `timeout_flag` must be `0` or `1`.
- Include sessions where players both succeeded and failed: the explanations are much more informative than when everyone has the same outcome.
- More sessions and more players give more reliable results.

### Where your data is stored

Each analysis creates a balancing session in `data/balancing_sessions/` inside the tool's folder, with your uploads and results. To start fresh, delete that folder. A technical log for troubleshooting is kept in `data/logs/server.log`.

The interface loads its fonts from Google Fonts; nothing else is contacted while you use the tool.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| *"Python 3.10 or newer was not found"* | Install Python (step 1). On Windows, make sure "Add python.exe to PATH" was ticked; if not, run the installer again and choose **Modify**. |
| *"Port 8001 / 8501 is already in use"* | The tool is probably already running in another window. Close it, or open http://localhost:8501. |
| *"This file is being run from inside the zip"* (Windows) | Extract the zip first (right-click → **Extract All…**) and start the tool from the extracted folder. |
| *"The path of this folder is too long"* (Windows) | Move the folder somewhere shorter, such as `C:\igame-game-balance-tool`, and start again. |
| Setup failed halfway | Check your internet connection and start again; setup restarts from the beginning. |
| The browser did not open | Open http://localhost:8501 yourself. |
| Something else | See `data/logs/server.log`, or open an issue on the GitHub repository. |

To reinstall from scratch, delete the hidden `.venv` folder inside the tool's folder and start again. To remove the tool completely, delete its folder; nothing is installed anywhere else.

---

## For developers

### Running manually

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python run.py                          # API on http://127.0.0.1:8001 (docs at /docs)
streamlit run app/streamlit_app.py     # interface, in a second terminal
```

Ports can be changed with the environment variables `GB_API_PORT` and `GB_UI_PORT` (used by `launcher.py`), or `API_BASE_URL` for the interface.

### Using the API directly

You can skip the interface and send data straight from your game or pipeline:

| Method | Path | Description |
|---|---|---|
| `POST` | `/analyze` | Upload telemetry (multipart file); returns analysis, recommendations and a `session_id` |
| `POST` | `/session/{id}/applied` | Record which recommendations were applied |
| `POST` | `/session/{id}/iteration` | Upload follow-up data for an existing balancing session |
| `GET` | `/session/{id}` | Session metadata and iteration summary |
| `GET` | `/families` | List the gameplay data types |
| `GET` | `/docs` | Interactive API documentation |

Upload format:

```json
{
  "gameplay_instance": {
    "instance_id": "my_game_001",
    "start_condition": "player enters the maze",
    "end_condition": "player reaches the exit or time expires",
    "success_condition": "player reaches the exit",
    "failure_condition": "player times out",
    "telemetry_family": "pathfinding"
  },
  "events": [ ... ]
}
```

The templates in `templates/` show the full list of fields for each gameplay data type.

### How the analysis works

1. **Validation:** events are checked for required fields, types, ranges and contradictions; invalid events are skipped and reported.
2. **Feature extraction:** events are aggregated into per-session features for the chosen gameplay data type. Averages, counts and rates are computed over action events only.
3. **Behavioural clusters:** players are grouped by their overall play pattern (K-Means). Clusters are descriptive only: they never decide which recommendation fires, but a note is added when a problem is concentrated in one group of players.
4. **Prediction and explanation:** a Gradient Boosting model predicts session success, and SHAP explains which features drive it. With a single outcome in the data, features are ranked by their relative variability instead, and a warning says so.
5. **Recommendations:** transparent, threshold-based design rules turn the measured problems into prioritised recommendations (high, medium, low). A problem is only reported when its measured value crosses the rule's threshold; when the same metric is also among the two strongest SHAP factors, its priority is raised by one level. Each level keeps its four most important recommendations.
6. **Comparing versions:** after a follow-up upload, problems are matched by level and problem type, so you see which were resolved, which persist (with the before → after value) and which are new.

### Adding a gameplay data type

1. `families/<type>/config.py`: define `REQUIRED_FIELDS`, `OPTIONAL_DEFAULTS`, `FEATURE_COLS`.
2. `families/<type>/extractor.py`: implement `aggregate_sessions(events) -> pd.DataFrame`.
3. `families/<type>/rules.py`: implement `generate_recommendations(level_id, level_df, success_rate, top_features, per_archetype=None)` and end it with `return finalize(recs, per_archetype)` (`shared/rule_utils.py`).
4. Register it in `core/registry.py`.

---

## License

The license for this tool will be added soon. Third-party components and their licenses are listed in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

## Acknowledgement

Developed by CERTH-ITI within the **i-Game** project.

Funded by the European Union under the Horizon Europe programme, grant agreement No 101132449. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority. Neither the European Union nor the granting authority can be held responsible for them.
