"""
app/streamlit_app.py
Game Balance Tool v3.1
Dark arcade aesthetic UI.
"""
import json
import io
import os

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8001")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
FAMILIES = ["game_jam_generic", "pathfinding", "puzzle_interaction", "strategy_combat", "accessibility_precision"]

FAMILY_DISPLAY_NAMES = {
    "game_jam_generic":        "Generic",
    "pathfinding":             "Pathfinding / Navigation",
    "puzzle_interaction":      "Puzzle / Interaction",
    "strategy_combat":         "Strategy / Combat",
    "accessibility_precision": "Accessibility / Precision",
}

FAMILY_REQUIRED_FIELDS = {
    "timestamp":          "ISO 8601 datetime — when the event occurred",
    "session_id":         "Unique identifier for the play session",
    "player_id":          "Player or agent identifier",
    "level_id":           "Level or scene identifier",
    "event_type":         "`level_start` | `action` | `level_end`",
    "decision_time_ms":   "Time spent before acting (ms)",
    "completion_time_ms": "Total level time recorded on `level_end`",
    "success_flag":       "`1` if the level was completed, `0` otherwise",
}

FAMILY_OPTIONAL_FIELDS = {
    "pathfinding": {
        "was_backtracked":  "`1` if this action was a backtrack move — default 0",
        "moves":            "Number of moves made in this event — default 0",
        "timeout_flag":     "`1` if this action ended in a timeout — default 0",
        "nodes_expanded":   "Search nodes expanded during pathfinding — default 0",
    },
    "puzzle_interaction": {
        "interaction_count":       "Number of object/player interactions — default 0",
        "wrong_interaction_count": "Number of incorrect or irrelevant interactions — default 0",
        "hint_count":              "Number of hints used or requested — default 0",
    },
    "strategy_combat": {
        "moves":          "Number of player actions/turns in this event — default 0",
        "damage_taken":   "Total damage received in this event — default 0",
        "deaths":         "Number of player deaths/failures in this event — default 0",
        "resource_loss":  "Amount of resources lost or spent unsuccessfully — default 0",
        "healing_usage":  "Number of healing or recovery actions taken — default 0",
    },
    "game_jam_generic": {},
    "accessibility_precision": {
        "error_count":           "integer — incorrect interactions or precision mistakes — default null",
        "assistance_used":       "integer — assistance features used (hints, snap, zoom, auto-complete) — default null",
        "idle_time_ms":          "float — longest inactivity period during the task (ms) — default null",
        "input_precision_score": "0–1 float — game-defined normalised precision score (% inside outline, placement accuracy, etc.) — default null",
        "undo_count":            "integer — undo or correction actions taken — default null",
    },
}

st.set_page_config(
    page_title="Game Balance Tool v3.0",
    page_icon="🕹️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS — dark arcade palette
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Share+Tech+Mono&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    background-color: #0a0a0f;
    color: #e0e0f0;
}

/* ── App background ── */
.stApp {
    background: #0a0a0f;
    background-image:
        linear-gradient(rgba(0,255,180,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,180,0.03) 1px, transparent 1px);
    background-size: 32px 32px;
}

/* ── Title ── */
h1 {
    font-family: 'Press Start 2P', monospace !important;
    font-size: 1.1rem !important;
    color: #00ffb4 !important;
    text-shadow: 0 0 20px #00ffb4aa, 0 0 40px #00ffb455;
    letter-spacing: 2px;
    line-height: 1.8 !important;
    padding-bottom: 0.5rem;
}

/* ── Section headers ── */
h2 {
    font-family: 'Press Start 2P', monospace !important;
    font-size: 0.65rem !important;
    color: #ff6aff !important;
    text-shadow: 0 0 12px #ff6aff88;
    letter-spacing: 3px;
    text-transform: uppercase;
    border-left: 3px solid #ff6aff;
    padding-left: 12px;
    margin-top: 2rem !important;
}

/* ── Subheaders ── */
h3 {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.9rem !important;
    color: #ffe066 !important;
    letter-spacing: 1px;
}

/* ── Body text ── */
p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.82rem !important;
    color: #c0c8e0;
}

/* ── Inputs ── */
input[type="text"], .stTextInput input, .stSelectbox select {
    background: #12121e !important;
    border: 1px solid #2a2a4a !important;
    border-radius: 3px !important;
    color: #00ffb4 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.8rem !important;
}
input[type="text"]:focus, .stTextInput input:focus {
    border-color: #00ffb4 !important;
    box-shadow: 0 0 8px #00ffb455 !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: #12121e !important;
    border: 1px solid #2a2a4a !important;
    color: #00ffb4 !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00ffb4 0%, #00c896 100%) !important;
    color: #000000 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 1.2rem !important;
    font-weight: 900 !important;
    border: none !important;
    border-radius: 3px !important;
    padding: 0.75rem 1.5rem !important;
    letter-spacing: 2px;
    box-shadow: 0 0 30px #00ffb477, 6px 6px 0 #00705a;
    transform: none !important;
    transition: none !important;
    cursor: pointer;
    outline: none !important;
}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[kind="primary"] div {
    color: #000000 !important;
    font-weight: 900 !important;
    transition: none !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[kind="primary"]:focus,
.stButton > button[kind="primary"]:active,
.stButton > button[kind="primary"]:hover p,
.stButton > button[kind="primary"]:hover span,
.stButton > button[kind="primary"]:focus p,
.stButton > button[kind="primary"]:focus span {
    background: linear-gradient(135deg, #00ffb4 0%, #00c896 100%) !important;
    color: #000000 !important;
    font-weight: 900 !important;
    box-shadow: 0 0 30px #00ffb477, 6px 6px 0 #00705a !important;
    transform: none !important;
    transition: none !important;
    border: none !important;
    outline: none !important;
    filter: none !important;
}
.stButton > button[kind="primary"]:disabled,
.stButton > button[kind="primary"]:disabled p,
.stButton > button[kind="primary"]:disabled span {
    color: #000000 !important;
    font-weight: 900 !important;
    opacity: 0.45 !important;
    transform: none !important;
    transition: none !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
}

/* ── Secondary / download buttons ── */
.stDownloadButton > button, .stButton > button {
    background: #1e0a2e !important;
    color: #ffffff !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.9rem !important;
    font-weight: 700 !important;
    border: 1px solid #ff6aff !important;
    border-radius: 3px !important;
    box-shadow: 0 0 12px #ff6aff55 !important;
    transition: none !important;
}
.stDownloadButton > button p,
.stDownloadButton > button span,
.stButton > button p,
.stButton > button span {
    color: #ffffff !important;
    font-weight: 700 !important;
    transition: none !important;
}
.stDownloadButton > button:hover,
.stDownloadButton > button:focus,
.stButton > button:hover,
.stButton > button:focus,
.stDownloadButton > button:hover p,
.stButton > button:hover p,
.stDownloadButton > button:hover span,
.stButton > button:hover span {
    background: #1e0a2e !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border: 1px solid #ff6aff !important;
    box-shadow: 0 0 12px #ff6aff55 !important;
    transform: none !important;
    transition: none !important;
    filter: none !important;
    outline: none !important;
}

/* ── File uploader ── */
.stFileUploader {
    background: #0d0d1a !important;
    border: 2px dashed #2a2a5a !important;
    border-radius: 4px !important;
    padding: 1rem;
    transition: border-color 0.2s;
}
.stFileUploader:hover {
    border-color: #00ffb4 !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: #0d0d1a !important;
    border: 1px solid #1e1e3a !important;
    border-radius: 4px !important;
    padding: 1rem !important;
    box-shadow: inset 0 0 20px #00ffb408;
}
[data-testid="metric-container"] label {
    color: #7080b0 !important;
    font-size: 0.65rem !important;
    font-family: 'Press Start 2P', monospace !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #00ffb4 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 1.4rem !important;
    text-shadow: 0 0 10px #00ffb466;
}

/* ── Info / warning / error boxes ── */
.stInfo, [data-testid="stInfo"] {
    background: #0d1a2a !important;
    border-left: 3px solid #3090ff !important;
    font-family: 'Share Tech Mono', monospace !important;
}
.stWarning, [data-testid="stAlert"][data-baseweb="notification"] {
    background: #1a1200 !important;
    border-left: 3px solid #ffe066 !important;
}
.stError {
    background: #1a0a0a !important;
    border-left: 3px solid #ff4060 !important;
}
.stSuccess {
    background: #0a1a12 !important;
    border-left: 3px solid #00ffb4 !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #0d0d1a !important;
    border: 1px solid #1e1e3a !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.8rem !important;
    color: #8090c0 !important;
}
.streamlit-expanderContent {
    background: #0a0a14 !important;
    border: 1px solid #1e1e3a !important;
    border-top: none !important;
}

/* ── Container / card ── */
[data-testid="stVerticalBlock"] > [data-testid="element-container"] > div[data-testid="stVerticalBlock"] {
    background: #0d0d1a;
    border: 1px solid #1e1e3a;
    border-radius: 4px;
    padding: 1rem;
}

/* ── Divider ── */
hr {
    border-color: #1e1e3a !important;
}

/* ── DataFrame / table ── */
.stDataFrame {
    background: #0d0d1a !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.75rem !important;
}

/* ── Code / monospace ── */
code, pre {
    background: #0d0d1a !important;
    color: #00ffb4 !important;
    font-family: 'Share Tech Mono', monospace !important;
    border: 1px solid #1e1e3a !important;
    border-radius: 3px !important;
}

/* ── Caption ── */
small, .stCaption {
    font-family: 'Share Tech Mono', monospace !important;
    color: #4a5070 !important;
    font-size: 0.72rem !important;
}

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: #00ffb4 !important;
}

/* ── Rec cards ── */
.rec-card {
    background: #0d0d1a;
    border: 1px solid #1e1e3a;
    border-radius: 4px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
}
.rec-card.high   { border-left: 4px solid #ff4060; }
.rec-card.medium { border-left: 4px solid #ffe066; }
.rec-card.low    { border-left: 4px solid #00ffb4; }

</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def priority_badge(p: str) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p, "⚪")


def success_bar(rate: float, width: int = 12) -> str:
    filled = int(rate * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar}` {rate:.1%}"


def load_template(family: str) -> dict:
    path = os.path.join(TEMPLATE_DIR, f"{family}_template.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🕹️ GAME BALANCE TOOL")
st.markdown(
    "<p style='font-family: Share Tech Mono, monospace; color: #7080b0; font-size:0.8rem;'>"
    "v3.0 &nbsp;|&nbsp; telemetry analysis + design recommendations"
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ---------------------------------------------------------------------------
# ONBOARDING
# ---------------------------------------------------------------------------
with st.expander("👋 Welcome — read this first", expanded=True):

    st.markdown("### Welcome to the Game Balance Tool")
    st.markdown(
        "Use this tool to analyze gameplay data and receive recommendations "
        "about your game's difficulty and balance."
    )
    st.markdown(
        "The tool is designed for games that contain a clear objective within "
        "a level, mission, encounter, puzzle, or gameplay section."
    )

    st.markdown("---")
    st.markdown("### Before you begin")
    st.markdown(
        "Create a game instance that you would like to evaluate. "
        "Then playtest your game by:"
    )
    st.markdown(
        "- playing it yourself\n"
        "- asking players to test it\n"
        "- using AI agents\n"
        "- or combining multiple approaches"
    )
    st.markdown(
        "During each play session, record gameplay variables such as completion time, "
        "retries, mistakes, decisions, or other gameplay events."
    )

    st.markdown("---")
    st.markdown("### Choose a Gameplay Type")
    st.markdown(
        "We suggest different gameplay variables depending on the type of gameplay "
        "your game contains."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            "<div style='background:#0d0d1a; border:1px solid #1e1e3a; border-left:3px solid #185FA5; "
            "border-radius:4px; padding:10px 14px; margin-bottom:10px;'>"
            "<span style='color:#3a9fff; font-family:Share Tech Mono,monospace; font-size:0.78rem; font-weight:600;'>"
            "Pathfinding / Navigation</span><br>"
            "<span style='color:#8090c0; font-family:Share Tech Mono,monospace; font-size:0.74rem;'>"
            "Exploration, traversal, route finding, movement challenges.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='background:#0d0d1a; border:1px solid #1e1e3a; border-left:3px solid #534AB7; "
            "border-radius:4px; padding:10px 14px; margin-bottom:10px;'>"
            "<span style='color:#a090ff; font-family:Share Tech Mono,monospace; font-size:0.78rem; font-weight:600;'>"
            "Puzzle / Interaction</span><br>"
            "<span style='color:#8090c0; font-family:Share Tech Mono,monospace; font-size:0.74rem;'>"
            "Inventory puzzles, object interactions, point-and-click gameplay.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            "<div style='background:#0d0d1a; border:1px solid #1e1e3a; border-left:3px solid #993C1D; "
            "border-radius:4px; padding:10px 14px; margin-bottom:10px;'>"
            "<span style='color:#ff8060; font-family:Share Tech Mono,monospace; font-size:0.78rem; font-weight:600;'>"
            "Strategy / Combat</span><br>"
            "<span style='color:#8090c0; font-family:Share Tech Mono,monospace; font-size:0.74rem;'>"
            "Resource management, combat encounters, tactical decisions.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='background:#0d0d1a; border:1px solid #1e1e3a; border-left:3px solid #0F6E56; "
            "border-radius:4px; padding:10px 14px; margin-bottom:10px;'>"
            "<span style='color:#00ffb4; font-family:Share Tech Mono,monospace; font-size:0.78rem; font-weight:600;'>"
            "Accessibility / Precision</span><br>"
            "<span style='color:#8090c0; font-family:Share Tech Mono,monospace; font-size:0.74rem;'>"
            "Precision-based interactions, tracing, coloring, drag-and-drop, and interaction accuracy.</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "If more than one gameplay type seems suitable, feel free to experiment "
        "with different options and compare the results."
    )
    st.markdown(
        "A JSON example will be generated automatically based on your selection. "
        "Use this example as a guide for structuring your gameplay data."
    )
    st.info(
        "Not sure which gameplay type to choose? Start with the **Generic** option. "
        "You can always try other gameplay types later and compare the results."
    )

    st.markdown("---")
    st.markdown("### Upload Your Data")
    st.markdown(
        "After collecting gameplay data, upload the generated JSON file. "
        "The tool will analyze the data and generate gameplay insights and "
        "game balance recommendations."
    )

    st.markdown("---")
    st.markdown("### For Better Results")
    st.markdown(
        "Try to collect multiple play sessions and different gameplay behaviours. For example:"
    )
    st.markdown(
        "- successful runs\n"
        "- unsuccessful runs\n"
        "- cautious players\n"
        "- exploratory players\n"
        "- speed-focused players"
    )
    st.markdown(
        "More diverse play styles generally lead to more robust and inclusive recommendations."
    )
    st.markdown(
        "**Recommended minimum:**\n"
        "- 10–20 play sessions for initial analysis\n"
        "- 30+ play sessions when possible"
    )

st.divider()

# ---------------------------------------------------------------------------
# SECTION 1 — Gameplay Instance
# ---------------------------------------------------------------------------
st.header("01 // GAMEPLAY INSTANCE")
st.markdown(
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; color:#8090c0; "
    "margin-bottom:20px;'>Choose a Gameplay Type and get suggested metrics in JSON format.</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Instance ID counter — auto-increments on Reset, resets to 1 on fresh load
# ---------------------------------------------------------------------------
if "_instance_counter" not in st.session_state:
    st.session_state["_instance_counter"] = 1

def _make_instance_id(gname: str, counter: int) -> str:
    """Generate a readable instance ID from game name + counter."""
    import re as _re
    safe = _re.sub(r"[^\w]", "_", gname.strip().lower())
    safe = _re.sub(r"_+", "_", safe).strip("_")[:30] or "game"
    return f"{safe}_{counter:03d}"

# ---------------------------------------------------------------------------
# Game Name
# ---------------------------------------------------------------------------
_saved_game_name = st.session_state.get("_game_name_saved", "game_001")
game_name = st.text_input(
    "Game Name",
    value=_saved_game_name,
    placeholder="e.g. Ant Colony, Coloring Game, Dungeon Crawler...",
    help="Enter the name of the game you want to analyze.",
)
# Persist game name so Reset can keep it
st.session_state["_game_name_saved"] = game_name

# ---------------------------------------------------------------------------
# Gameplay Data Type
# ---------------------------------------------------------------------------
st.markdown(
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.85rem; color:#ffe066; "
    "margin-bottom:4px;'>Select your Gameplay Data Type</p>"
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; color:#8090c0; "
    "margin-bottom:12px;'>Choose the type that best matches your game. "
    "This determines which gameplay variables and recommendations apply.</p>",
    unsafe_allow_html=True,
)
_saved_family_idx = st.session_state.get("_family_idx_saved", 0)
telemetry_family = st.selectbox(
    "Gameplay Data Type (Telemetry Family)",
    FAMILIES,
    index=_saved_family_idx,
    format_func=lambda x: FAMILY_DISPLAY_NAMES.get(x, x),
    help="Not sure? Start with Generic — it works for any game type.",
)
st.session_state["_family_idx_saved"] = FAMILIES.index(telemetry_family)

# ---------------------------------------------------------------------------
# Session actions — only shown after at least one session has been run
# ---------------------------------------------------------------------------
if st.session_state.get("_analysis_complete") or st.session_state.get("_followup_complete"):
    st.markdown(
        "<div style='background:#0d0d1a; border:1px solid #1e1e3a; border-radius:4px; "
        "padding:14px 18px; margin-bottom:12px; margin-top:16px;'>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.80rem; "
        "color:#a0aac0; margin:0 0 10px 0;'>"
        "✅ <strong>You've analysed a session.</strong> Would you like to start over?"
        "</p>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.74rem; "
        "color:#7080a0; margin:0 0 6px 0;'>"
        "🔄 <strong style='color:#a0aac0;'>Keep Setup &amp; Start Over</strong> — "
        "use this if you are continuing with the same gameplay section. Your gameplay type and conditions "
        "will all be kept exactly as they are, so you don't have to re-enter them. "
        "Only the analysis results are cleared."
        "</p>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.74rem; "
        "color:#7080a0; margin:0;'>"
        "✨ <strong style='color:#a0aac0;'>Start Fresh</strong> — "
        "use this if you are moving to a different gameplay section, level, layout, or encounter. "
        "Everything is cleared including the gameplay type and conditions, "
        "so you can describe the new section from scratch."
        "</p></div>",
        unsafe_allow_html=True,
    )
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Keep Setup & Start Over", key="reset_keep_btn",
                     help="Same gameplay section — keeps your gameplay type and all conditions. Only clears the results."):
            st.session_state["_instance_counter"] += 1
            for key in [
                "_analysis_complete", "_result", "_analysis", "_recommendations",
                "_followup_complete", "_followup_result", "_followup_analysis",
                "_followup_recommendations", "_followup_file_bytes", "applied_recs",
                "session_id", "current_iteration",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["_reset_note"] = "keep"
            st.rerun()
    with col_btn2:
        if st.button("✨ Start Fresh", key="reset_fresh_btn",
                     help="New gameplay section, level, or layout — clears everything including gameplay type and conditions."):
            st.session_state["_instance_counter"] += 1
            for key in [
                "_analysis_complete", "_result", "_analysis", "_recommendations",
                "_followup_complete", "_followup_result", "_followup_analysis",
                "_followup_recommendations", "_followup_file_bytes", "applied_recs",
                "session_id", "current_iteration",
                "_family_idx_saved", "_start_cond", "_end_cond",
                "_success_cond", "_failure_cond",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["_reset_note"] = "fresh"
            st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Gameplay instance conditions
# ---------------------------------------------------------------------------
_reset_note = st.session_state.pop("_reset_note", None)
if _reset_note == "keep":
    st.success(
        "Previous session data has been saved. "
        "Your gameplay type and conditions are kept — ready to collect new data for the same section."
    )
elif _reset_note == "fresh":
    st.success(
        "Previous session data has been saved. "
        "Setup cleared — describe your new gameplay section below."
    )

st.markdown(
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.85rem; color:#ffe066; "
    "margin-bottom:2px;'>Define your gameplay instance "
    "<span style='color:#8090c0; font-size:0.78rem; font-weight:normal;'>"
    "— Describe what you are testing</span></p>"
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; color:#8090c0; "
    "margin-bottom:4px;'>Choose the part of your game you want to evaluate, such as a level, "
    "puzzle, quest, tutorial, mission, or combat encounter.</p>"
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.75rem; color:#506080; "
    "margin-bottom:12px;'>These fields are descriptive and help the tool understand what is "
    "being evaluated. They are not gameplay metrics.</p>",
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    start_condition   = st.text_input(
        "Start Condition",
        value=st.session_state.get("_start_cond", "player starts level"),
        key="start_cond_input",
    )
    end_condition     = st.text_input(
        "End Condition",
        value=st.session_state.get("_end_cond", "level complete or player quits"),
        key="end_cond_input",
    )
with col2:
    success_condition = st.text_input(
        "Success Condition",
        value=st.session_state.get("_success_cond", "player reaches goal"),
        key="success_cond_input",
    )
    failure_condition = st.text_input(
        "Failure Condition",
        value=st.session_state.get("_failure_cond", "player quits or time expires"),
        key="failure_cond_input",
    )

# Persist conditions for Reset
st.session_state["_start_cond"]   = start_condition
st.session_state["_end_cond"]     = end_condition
st.session_state["_success_cond"] = success_condition
st.session_state["_failure_cond"] = failure_condition

# Auto-generated instance ID (hidden from main UI)
instance_id = _make_instance_id(game_name, st.session_state["_instance_counter"])

# Advanced details expander — shows generated IDs for reference
with st.expander("🔧 Advanced details (auto-generated — not required from you)", expanded=False):
    st.markdown(
        f"<p style='font-family:Share Tech Mono,monospace; font-size:0.74rem; color:#8090c0;'>"
        f"These identifiers are generated automatically and used in saved files.<br>"
        f"<strong>Instance ID:</strong> <code>{instance_id}</code><br>"
        f"<strong>Session ID:</strong> generated on first analysis as "
        f"<code>{_make_instance_id(game_name, st.session_state['_instance_counter'])}"
        f"_DDMMYY_HHMMSS</code>"
        f"</p>",
        unsafe_allow_html=True,
    )

gameplay_instance = {
    "instance_id":       instance_id,
    "start_condition":   start_condition,
    "end_condition":     end_condition,
    "success_condition": success_condition,
    "failure_condition": failure_condition,
    "telemetry_family":  telemetry_family,
}

st.divider()

# ---------------------------------------------------------------------------
# SECTION 2 — Field Reference
# ---------------------------------------------------------------------------
st.header("02 // TELEMETRY SCHEMA")

with st.expander("📋 What is a gameplay event?", expanded=True):
    st.markdown(
        "A gameplay event is a recorded moment during playtesting."
    )
    st.markdown(
        "- **`level_start`** → gameplay begins\n"
        "- **`action`** → a player action or interaction occurs\n"
        "- **`level_end`** → gameplay ends"
    )
    st.markdown(
        "A play session usually contains one `level_start`, multiple `action` events, and one `level_end`."
    )
    st.markdown("**Example:**")
    st.code(
        "level_start\n"
        "action  (move)\n"
        "action  (pick up item)\n"
        "action  (open door)\n"
        "action  (solve puzzle)\n"
        "level_end",
        language=None,
    )
    st.markdown("Each row in the JSON file represents one gameplay event.")

st.markdown(f"Event fields for the **{FAMILY_DISPLAY_NAMES.get(telemetry_family, telemetry_family)}** Gameplay Data Type:")

with st.expander("📋 Required fields (all Gameplay Types)", expanded=True):
    st.markdown(
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.76rem; color:#8090c0; "
        "margin-bottom:10px;'>"
        "These fields are used to identify players, sessions, levels, and gameplay events. "
        "They allow the tool to group gameplay events into complete play sessions and analyze them correctly. "
        "They are required for all Gameplay Types."
        "</p>",
        unsafe_allow_html=True,
    )
    for field, desc in FAMILY_REQUIRED_FIELDS.items():
        st.markdown(f"- **`{field}`** — {desc}")

optional_fields = FAMILY_OPTIONAL_FIELDS.get(telemetry_family, {})
with st.expander(f"📋 Optional Gameplay Variables for {FAMILY_DISPLAY_NAMES.get(telemetry_family, telemetry_family)}"):
    st.markdown(
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.76rem; color:#8090c0; "
        "margin-bottom:10px;'>"
        "These variables describe how players interact with your game during playtesting. "
        "The suggested variables depend on the gameplay type you selected. "
        "You can record only the variables that are relevant to your game."
        "</p>",
        unsafe_allow_html=True,
    )
    if optional_fields:
        for field, desc in optional_fields.items():
            st.markdown(f"- **`{field}`** — {desc}")
    else:
        st.markdown(
            "_The Generic gameplay type has no specific optional variables. "
            "Use the General Gameplay Variables below to capture game-specific metrics._"
        )

with st.expander("📋 General Gameplay Variables (all Gameplay Types, all optional)"):
    st.markdown(
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.76rem; color:#8090c0; "
        "margin-bottom:10px;'>"
        "These optional variables can be used with any gameplay type. "
        "They are useful for game-specific mechanics that are not fully captured by the suggested gameplay variables."
        "</p>",
        unsafe_allow_html=True,
    )
    generic_info = {
        "objective_progress":    "0–1 float — how far toward the level objective the player reached. Aggregated as **max** per session.",
        "system_state_score":    "0–1 float — overall game-world state quality at this point. Aggregated as **last** (final state) per session.",
        "positive_action_count": "integer — number of actions that moved the player toward the goal. Aggregated as **sum** per session.",
        "negative_action_count": "integer — number of actions that moved the player away from the goal. Aggregated as **sum** per session.",
        "influence_score":       "0–1 float — how strongly the player's actions affected another system (NPCs, environment, factions). Aggregated as **mean**. Excluded from ML by default — opt in via `INFLUENCE_SCORE_ENABLED`.",
        "custom_game_score":     "number — developer-defined numeric score, any scale. Aggregated as **last** (final score) per session.",
    }
    for field, desc in generic_info.items():
        st.markdown(f"- **`{field}`** — {desc}")

try:
    template = load_template(telemetry_family)
    template["gameplay_instance"] = gameplay_instance
    template_bytes = json.dumps(template, indent=2).encode("utf-8")
    st.download_button(
        label="⬇ Download JSON Template",
        data=template_bytes,
        file_name=f"{telemetry_family}_template.json",
        mime="application/json",
    )
except Exception as e:
    st.warning(f"Could not load template: {e}")

st.divider()

# ---------------------------------------------------------------------------
# SECTION 3 — Upload
# ---------------------------------------------------------------------------
st.header("03 // UPLOAD & ANALYZE")
st.markdown(
    "Upload a `.json` (preferred) or `.jsonl` telemetry file from your jam session. "
    "The Gameplay Instance fields above will be merged into the request."
)

uploaded_file = st.file_uploader(
    "DROP TELEMETRY FILE HERE",
    type=["json", "jsonl"],
    help="JSON: {gameplay_instance, events:[...]}  |  JSONL: one event per line",
)

run_btn = st.button(
    "▶  RUN ANALYSIS",
    type="primary",
    disabled=uploaded_file is None or not game_name.strip(),
)

if not game_name.strip() and uploaded_file is not None:
    st.markdown(
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.75rem; color:#ffe066; "
        "margin-top:6px;'>⚠️ Enter a Game Name in Section 01 to enable analysis.</p>",
        unsafe_allow_html=True,
    )
elif not game_name.strip():
    st.markdown(
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.75rem; color:#506080; "
        "margin-top:6px;'>Upload a file and enter a Game Name in Section 01 to run analysis.</p>",
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# SECTION 4 — Results
# ---------------------------------------------------------------------------
st.header("04 // RESULTS")

# ---------------------------------------------------------------------------
# On every rerun (including checkbox clicks), restore from session_state.
# Only call the API when run_btn was just clicked.
# ---------------------------------------------------------------------------
if run_btn and uploaded_file is not None:
    raw_bytes = uploaded_file.read()
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
        if isinstance(payload, dict):
            payload["gameplay_instance"] = gameplay_instance
        elif isinstance(payload, list):
            payload = {"gameplay_instance": gameplay_instance, "events": payload}
        merged_bytes = json.dumps(payload).encode("utf-8")
    except Exception:
        merged_bytes = raw_bytes

    with st.spinner("PROCESSING TELEMETRY…"):
        try:
            resp = requests.post(
                f"{API_BASE}/analyze",
                files={"file": ("upload.json", io.BytesIO(merged_bytes), "application/json")},
                data={"game_name": game_name.strip()},
                timeout=60,
            )
            try:
                _result = resp.json()
            except Exception:
                st.error(
                    f"⚠️ The API returned an unexpected response (HTTP {resp.status_code}).\n\n"
                    f"```\n{resp.text[:500]}\n```"
                )
                _result = None
        except requests.exceptions.ConnectionError:
            st.error(
                f"⚠️ Cannot reach API at `{API_BASE}`. "
                "Start the server first:\n\n```bash\npython run.py\n```"
            )
            _result = None
        except Exception as e:
            st.error(f"Request failed: {e}")
            _result = None

    if _result is not None:
        if _result.get("status") == "error" or _result.get("errors"):
            st.error("### ❌ ANALYSIS FAILED")
            for err in _result.get("errors", []):
                st.error(err)
            with st.expander("Raw response"):
                st.json(_result)
        else:
            # Store everything in session_state — persists across all future reruns
            st.session_state["_analysis_complete"]   = True
            st.session_state["_result"]              = _result
            st.session_state["_analysis"]            = _result.get("analysis", {})
            st.session_state["_recommendations"]     = _result.get("recommendations", [])
            if _result.get("session_id"):
                st.session_state["session_id"]           = _result["session_id"]
                st.session_state["current_iteration"]    = 1

# Retrieve from session_state (works on initial run and all subsequent reruns)
analysis_complete = st.session_state.get("_analysis_complete", False)
result            = st.session_state.get("_result", None)
analysis          = st.session_state.get("_analysis", {})
recommendations   = st.session_state.get("_recommendations", [])

if not analysis_complete:
    st.info("Upload a telemetry file and click **▶ RUN ANALYSIS** to see results.")
else:
    warnings = analysis.get("warnings", [])

    WARNING_TITLES = {
        "MISSING_OPTIONAL_FIELDS": "Some optional fields were not included in your data",
        "MISSING_GENERIC_FIELDS":  "General gameplay variables were not included in your data",
        "MISSING_GENERAL_FIELDS":  "General gameplay variables were not included in your data",
        "LOW_SESSION_COUNT":       "Not enough sessions for full ML analysis",
        "LOW_TELEMETRY_COVERAGE":  "Low telemetry coverage — check Gameplay Data Type or logging setup",
        "RECOMMENDATION_FAILED":   "Recommendation engine encountered an error",
        "INVALID_EVENTS":          "Some events were skipped due to validation errors",
    }
    for w in warnings:
        if "|" in w:
            code, message = w.split("|", 1)
            title = WARNING_TITLES.get(code.strip(), code.strip())
            with st.warning(f"⚠️ **{title}**"):
                pass
            st.markdown(
                f"<div style='background:#1a1200; border-left:3px solid #ffe066; "
                f"border-top:0.5px solid #2a2200; border-right:0.5px solid #2a2200; "
                f"border-bottom:0.5px solid #2a2200; border-radius:0 4px 4px 0; "
                f"padding:10px 14px; margin-top:-12px; margin-bottom:12px; "
                f"font-family:Share Tech Mono,monospace; font-size:0.78rem; color:#c0a850;'>"
                f"{message.strip()}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.warning(w)

    # --- Summary metrics ---
    st.subheader("OVERVIEW")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SESSIONS",     analysis.get("n_sessions", "—"))
    m2.metric("LEVELS",       analysis.get("n_levels",   "—"))
    m3.metric("PLAYERS",      analysis.get("n_agents",   "—"))
    m4.metric("OVERALL PASS", f"{analysis.get('overall_success_rate', 0):.1%}")

    st.markdown("**Level difficulty ranking** (hardest → easiest):")
    levels = analysis.get("levels_by_difficulty", [])
    if levels:
        cols = st.columns(min(len(levels), 4))
        for i, lv in enumerate(levels):
            cols[i % 4].markdown(
                f"**`{lv['level_id']}`**\n\n{success_bar(lv['success_rate'])}"
            )

    per_agent = analysis.get("per_agent", [])
    if per_agent:
        with st.expander("👾 Per-player breakdown", expanded=False):
            import pandas as pd
            df_a = pd.DataFrame(per_agent)
            df_a.columns = [c.replace("_", " ").upper() for c in df_a.columns]
            st.dataframe(df_a, width="stretch")

    # --- Recommendations with "Mark as applied" checkboxes ---
    st.subheader("DESIGN RECOMMENDATIONS")
    st.markdown(
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.75rem; color:#8090c0; "
        "margin-bottom:12px;'>Tick the recommendations you plan to apply before uploading "
        "the next version of your game in Section 05.</p>",
        unsafe_allow_html=True,
    )

    if not recommendations:
        st.success("✅ No significant issues detected across all levels.")
    else:
        high   = [r for r in recommendations if r.get("priority") == "high"]
        medium = [r for r in recommendations if r.get("priority") == "medium"]
        low    = [r for r in recommendations if r.get("priority") == "low"]

        if "applied_recs" not in st.session_state:
            st.session_state.applied_recs = {}

        def render_group(recs, label):
            if not recs:
                return
            st.markdown(f"**{label}**")
            for idx, rec in enumerate(recs):
                badge   = priority_badge(rec.get("priority", "low"))
                rec_key = f"rec_{rec.get('level_id','')}_{idx}_{rec.get('priority','')}"
                with st.container(border=True):
                    col_check, col_content = st.columns([0.05, 0.95])
                    with col_check:
                        checked = st.checkbox("Applied", key=rec_key,
                                              label_visibility="collapsed")
                        st.session_state.applied_recs[rec_key] = (rec, checked)
                    with col_content:
                        st.markdown(
                            f"{badge} **`{rec.get('level_id', '?')}`** — {rec.get('problem', '')}"
                        )
                        c1, c2 = st.columns(2)
                        c1.markdown(f"🔬 *{rec.get('technical_reason', '')}*")
                        c2.markdown(f"🛠 **Fix:** {rec.get('suggestion', '')}")
                        st.markdown(f"📈 **Impact:** {rec.get('expected_impact', '')}")

        render_group(high,   "🔴 HIGH PRIORITY")
        render_group(medium, "🟡 MEDIUM PRIORITY")
        render_group(low,    "🟢 LOW PRIORITY")

    # Subtle session reference
    if st.session_state.get("session_id"):
        st.markdown(
            f"<p style='font-family:Share Tech Mono,monospace; font-size:0.70rem; "
            f"color:#3a4060; margin-top:16px;'>"
            f"🗄 Balancing session saved: "
            f"<code>session_{st.session_state.session_id}</code>"
            f"</p>",
            unsafe_allow_html=True,
        )

    # Note when follow-up has been submitted
    if st.session_state.get("_followup_complete"):
        st.markdown(
            "<p style='font-family:Share Tech Mono,monospace; font-size:0.75rem; "
            "color:#00ffb4; margin-top:8px;'>"
            "📊 Follow-up uploaded. See Section 05 for the comparison."
            "</p>",
            unsafe_allow_html=True,
        )

    with st.expander("🗂 Raw API response (JSON)", expanded=False):
        st.json(result)


st.divider()

# ---------------------------------------------------------------------------
# SECTION 5 — Compare After Changes
# ---------------------------------------------------------------------------
st.header("05 // COMPARE AFTER CHANGES")
st.markdown(
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.70rem; color:#506080; "
    "margin-bottom:16px;'>"
    "Section 04 = What should I change next? &nbsp;|&nbsp; "
    "Section 05 = What changed since the baseline?"
    "</p>",
    unsafe_allow_html=True,
)

_baseline_exists  = st.session_state.get("_analysis_complete", False)
_followup_exists  = st.session_state.get("_followup_complete", False)
_session_locked   = _followup_exists  # one follow-up per session

# ---------------------------------------------------------------------------
# LOCKED — no baseline yet
# ---------------------------------------------------------------------------
if not _baseline_exists:
    st.markdown(
        "<div style='background:#0d0d1a; border:1px solid #1e1e3a; border-radius:4px; padding:16px 20px;'>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; "
        "color:#8090c0; margin-bottom:10px;'>"
        "<strong style='color:#a0aac0;'>Before using this section:</strong></p>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.76rem; "
        "color:#8090c0; line-height:1.9; margin:0;'>"
        "1. Upload gameplay data and review the analysis in Section 04.<br>"
        "2. Select the recommendations you applied using the checkboxes in Section 04."
        "<br><br>"
        "<span style='color:#606880;'>Then, outside this tool:</span><br>"
        "3. Make changes to your game.<br>"
        "4. Collect new gameplay data from the updated version."
        "<br><br>"
        "<span style='color:#7080a0;'>Once you have the new JSON file, return here and upload it.</span>"
        "</p></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# UNLOCKED — baseline exists, no follow-up yet
# ---------------------------------------------------------------------------
elif not _followup_exists:
    st.markdown(
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; "
        "color:#8090c0; margin-bottom:16px;'>"
        "Review the recommendations in Section 04 and select the ones you applied. "
        "Then upload gameplay data from the updated version of your game. "
        "The tool will generate a new analysis and compare it with the baseline."
        "</p>",
        unsafe_allow_html=True,
    )

    # Show applied recommendations so far
    applied_list = [
        rec for rec, checked
        in st.session_state.get("applied_recs", {}).values()
        if checked
    ]
    if applied_list:
        with st.expander(
            f"✅ {len(applied_list)} recommendation(s) marked as applied",
            expanded=True
        ):
            for rec in applied_list:
                st.markdown(
                    f"- **`{rec.get('level_id','?')}`** — "
                    f"{rec.get('problem','')}"
                )
    else:
        st.info(
            "No recommendations marked as applied yet. "
            "Tick the ones you applied in Section 04 before uploading."
        )

    followup_file = st.file_uploader(
        "Upload Updated Gameplay Data",
        type=["json", "jsonl"],
        key="followup_upload",
        help="Upload the JSON telemetry file from your updated game build.",
    )

    # Store file bytes in session state as soon as a file is uploaded
    # so the button stays visible even if Streamlit reruns and clears the uploader
    if followup_file is not None:
        st.session_state["_followup_file_bytes"] = followup_file.read()

    _followup_ready = st.session_state.get("_followup_file_bytes") is not None

    if st.button("▶ ANALYZE FOLLOW-UP", type="primary", key="run_followup",
                 disabled=not _followup_ready):
        if _followup_ready:
            fu_bytes = st.session_state["_followup_file_bytes"]

            # Merge gameplay instance
            try:
                fu_payload = json.loads(fu_bytes.decode("utf-8"))
                if isinstance(fu_payload, dict):
                    fu_payload["gameplay_instance"] = gameplay_instance
                elif isinstance(fu_payload, list):
                    fu_payload = {"gameplay_instance": gameplay_instance,
                                  "events": fu_payload}
                fu_merged = json.dumps(fu_payload).encode("utf-8")
            except Exception:
                fu_merged = fu_bytes

            session_id = st.session_state.get("session_id", "")

            with st.spinner("ANALYZING FOLLOW-UP…"):
                fu_result = None
                try:
                    # Save applied recommendations
                    applied_list_state = [
                        rec for rec, checked
                        in st.session_state.get("applied_recs", {}).values()
                        if checked
                    ]
                    if session_id and applied_list_state:
                        requests.post(
                            f"{API_BASE}/session/{session_id}/applied",
                            data={
                                "next_iteration_number":   2,
                                "applied_recommendations": json.dumps(applied_list_state),
                            },
                            timeout=10,
                        )

                    # Run follow-up analysis
                    if session_id:
                        fu_resp = requests.post(
                            f"{API_BASE}/session/{session_id}/iteration",
                            files={"file": ("followup.json",
                                            io.BytesIO(fu_merged),
                                            "application/json")},
                            data={"iteration_number": 2,
                                  "gameplay_type": telemetry_family},
                            timeout=60,
                        )
                    else:
                        fu_resp = requests.post(
                            f"{API_BASE}/analyze",
                            files={"file": ("followup.json",
                                            io.BytesIO(fu_merged),
                                            "application/json")},
                            timeout=60,
                        )
                    try:
                        fu_result = fu_resp.json()
                    except Exception:
                        st.error(
                            f"⚠️ Unexpected API response (HTTP {fu_resp.status_code})."
                        )
                except requests.exceptions.ConnectionError:
                    st.error("⚠️ Cannot reach API. Make sure `python run.py` is running.")
                except Exception as e:
                    st.error(f"Request failed: {e}")

            if fu_result and fu_result.get("status") != "error":
                # Store follow-up in session state
                st.session_state["_followup_complete"]       = True
                st.session_state["_followup_result"]         = fu_result
                st.session_state["_followup_analysis"]       = fu_result.get("analysis", {})
                st.session_state["_followup_recommendations"] = fu_result.get("recommendations", [])
                # Clear stored file bytes — no longer needed
                st.session_state.pop("_followup_file_bytes", None)
                st.rerun()
            elif fu_result:
                st.error("### ❌ Follow-up Analysis Failed")
                for err in fu_result.get("errors", []):
                    st.error(err)

# ---------------------------------------------------------------------------
# FOLLOW-UP EXISTS — show analysis expander + comparison dashboard
# ---------------------------------------------------------------------------
else:
    fu_analysis = st.session_state.get("_followup_analysis", {})
    fu_recs     = st.session_state.get("_followup_recommendations", [])
    fu_result   = st.session_state.get("_followup_result", {})
    baseline    = st.session_state.get("_analysis", {})
    base_recs   = st.session_state.get("_recommendations", [])
    applied_list = [
        rec for rec, checked
        in st.session_state.get("applied_recs", {}).values()
        if checked
    ]

    st.success("✅ New analysis complete. See the comparison below.")

    # --- Collapsed follow-up analysis expander ---
    with st.expander("📊 Follow-up Analysis — full details", expanded=False):
        fu_warnings = fu_analysis.get("warnings", [])
        for w in fu_warnings:
            st.warning(w.split("|", 1)[-1] if "|" in w else w)

        fw1, fw2, fw3, fw4 = st.columns(4)
        fw1.metric("SESSIONS",     fu_analysis.get("n_sessions", "—"))
        fw2.metric("LEVELS",       fu_analysis.get("n_levels",   "—"))
        fw3.metric("PLAYERS",      fu_analysis.get("n_agents",   "—"))
        fw4.metric("OVERALL PASS", f"{fu_analysis.get('overall_success_rate', 0):.1%}")

        fu_levels = fu_analysis.get("levels_by_difficulty", [])
        if fu_levels:
            st.markdown("**Level difficulty ranking:**")
            fu_cols = st.columns(min(len(fu_levels), 4))
            for i, lv in enumerate(fu_levels):
                fu_cols[i % 4].markdown(
                    f"**`{lv['level_id']}`**\n\n{success_bar(lv['success_rate'])}"
                )

        fu_agent = fu_analysis.get("per_agent", [])
        if fu_agent:
            import pandas as pd
            df_fu = pd.DataFrame(fu_agent)
            df_fu.columns = [c.replace("_", " ").upper() for c in df_fu.columns]
            st.dataframe(df_fu, width="stretch")

        if fu_recs:
            st.markdown("**Follow-up recommendations:**")
            for rec in fu_recs:
                badge = priority_badge(rec.get("priority", "low"))
                with st.container(border=True):
                    st.markdown(
                        f"{badge} **`{rec.get('level_id','?')}`** — {rec.get('problem','')}"
                    )
                    st.markdown(f"🛠 **Fix:** {rec.get('suggestion','')}")
        else:
            st.success("No significant issues detected in the follow-up.")

        with st.expander("🗂 Raw follow-up response (JSON)", expanded=False):
            st.json(fu_result)

    st.divider()

    # --- Comparison dashboard ---
    st.subheader("BASELINE vs FOLLOW-UP")

    # Compute averages from per_level
    def _avg_metric(analysis_dict, field):
        levels = analysis_dict.get("per_level", {})
        if not levels:
            return None
        vals = []
        for lv in levels.values():
            v = lv.get(field)
            if v is not None and not (isinstance(v, float) and __import__('math').isnan(v)):
                vals.append(v)
        return sum(vals) / len(vals) if vals else None

    def _avg_from_agents(analysis_dict, field):
        agents = analysis_dict.get("per_agent", [])
        if not agents:
            return None
        vals = [a.get(field, 0) for a in agents if a.get(field) is not None]
        return sum(vals) / len(vals) if vals else None

    base_sr       = baseline.get("overall_success_rate", 0.0)
    fu_sr         = fu_analysis.get("overall_success_rate", 0.0)
    base_ct       = _avg_from_agents(baseline,   "mean_decision_time_ms")
    fu_ct         = _avg_from_agents(fu_analysis, "mean_decision_time_ms")
    base_retry    = _avg_from_agents(baseline,   "retry_count")
    fu_retry      = _avg_from_agents(fu_analysis, "retry_count")
    base_issues   = len([r for r in base_recs if r.get("priority") == "high"])
    fu_issues     = len([r for r in fu_recs   if r.get("priority") == "high"])

    # Metric cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "SUCCESS RATE",
        f"{fu_sr:.1%}",
        delta=f"{fu_sr - base_sr:+.1%}",
        help="Baseline → Follow-up"
    )
    c2.metric(
        "AVG DECISION TIME",
        f"{fu_ct/1000:.1f}s" if fu_ct is not None else "—",
        delta=f"{(fu_ct - base_ct)/1000:+.1f}s" if fu_ct and base_ct else None,
        delta_color="inverse",
        help="Average decision time per action across all sessions"
    )
    c3.metric(
        "AVG RETRY COUNT",
        f"{fu_retry:.1f}" if fu_retry is not None else "—",
        delta=f"{fu_retry - base_retry:+.1f}" if fu_retry and base_retry else None,
        delta_color="inverse",
        help="Average retries per session"
    )
    c4.metric(
        "HIGH ISSUES",
        fu_issues,
        delta=str(fu_issues - base_issues),
        delta_color="inverse",
        help="Number of high-priority recommendations"
    )

    st.divider()

    # --- Applied recommendations ---
    st.markdown("#### Applied Recommendations")
    if applied_list:
        for rec in applied_list:
            st.markdown(
                f"<div style='font-family:Share Tech Mono,monospace; font-size:0.76rem; "
                f"color:#00ffb4; padding:4px 0;'>"
                f"✓ <strong>`{rec.get('level_id','?')}`</strong> — "
                f"{rec.get('problem','')[:80]}{'…' if len(rec.get('problem','')) > 80 else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with st.expander("Full applied recommendation details", expanded=False):
            for rec in applied_list:
                with st.container(border=True):
                    st.markdown(f"**`{rec.get('level_id','?')}`** — {rec.get('problem','')}")
                    st.markdown(f"🛠 {rec.get('suggestion','')}")
                    st.markdown(f"📈 {rec.get('expected_impact','')}")
    else:
        st.markdown(
            "<p style='font-family:Share Tech Mono,monospace; font-size:0.75rem; "
            "color:#506080;'>No recommendations were marked as applied.</p>",
            unsafe_allow_html=True,
        )

    st.divider()

    # --- Resolved / Persisting / New ---
    st.markdown("#### Recommendation Impact")

    # Strict matching: same level_id AND same problem string
    base_set = {(r.get("level_id",""), r.get("problem","")): r for r in base_recs}
    fu_set   = {(r.get("level_id",""), r.get("problem","")): r for r in fu_recs}

    resolved   = [r for k, r in base_set.items() if k not in fu_set]
    persisting = [r for k, r in base_set.items() if k in fu_set]
    new_issues = [r for k, r in fu_set.items()  if k not in base_set]

    col_r, col_p, col_n = st.columns(3)

    with col_r:
        st.markdown(
            f"<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; "
            f"color:#00ffb4; font-weight:600;'>✅ Resolved ({len(resolved)})</p>",
            unsafe_allow_html=True,
        )
        if resolved:
            for rec in resolved:
                st.markdown(
                    f"<p style='font-family:Share Tech Mono,monospace; font-size:0.72rem; "
                    f"color:#00c896; margin:2px 0;'>"
                    f"**`{rec.get('level_id','?')}`** — "
                    f"{rec.get('problem','')[:60]}{'…' if len(rec.get('problem',''))>60 else ''}"
                    f"</p>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='font-family:Share Tech Mono,monospace; font-size:0.72rem; "
                "color:#3a4060;'>None</p>",
                unsafe_allow_html=True,
            )

    with col_p:
        st.markdown(
            f"<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; "
            f"color:#ffe066; font-weight:600;'>⚠️ Persisting ({len(persisting)})</p>",
            unsafe_allow_html=True,
        )
        if persisting:
            for rec in persisting:
                st.markdown(
                    f"<p style='font-family:Share Tech Mono,monospace; font-size:0.72rem; "
                    f"color:#c0a850; margin:2px 0;'>"
                    f"**`{rec.get('level_id','?')}`** — "
                    f"{rec.get('problem','')[:60]}{'…' if len(rec.get('problem',''))>60 else ''}"
                    f"</p>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='font-family:Share Tech Mono,monospace; font-size:0.72rem; "
                "color:#3a4060;'>None</p>",
                unsafe_allow_html=True,
            )

    with col_n:
        st.markdown(
            f"<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; "
            f"color:#ff6aff; font-weight:600;'>🆕 New ({len(new_issues)})</p>",
            unsafe_allow_html=True,
        )
        if new_issues:
            for rec in new_issues:
                st.markdown(
                    f"<p style='font-family:Share Tech Mono,monospace; font-size:0.72rem; "
                    f"color:#c060c0; margin:2px 0;'>"
                    f"**`{rec.get('level_id','?')}`** — "
                    f"{rec.get('problem','')[:60]}{'…' if len(rec.get('problem',''))>60 else ''}"
                    f"</p>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='font-family:Share Tech Mono,monospace; font-size:0.72rem; "
                "color:#3a4060;'>None</p>",
                unsafe_allow_html=True,
            )

    st.divider()

    # Session complete — two options
    st.markdown(
        "<div style='background:#0d0d1a; border:1px solid #1e1e3a; border-radius:4px; "
        "padding:16px 20px; margin-top:8px;'>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.82rem; "
        "color:#a0aac0; margin:0 0 14px 0;'>"
        "🔒 <strong>This session is complete.</strong> Your results have been saved."
        "</p>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.76rem; "
        "color:#8090c0; margin:0 0 10px 0;'>"
        "What would you like to do next?"
        "</p>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.75rem; "
        "color:#7080a0; margin:0 0 8px 0;'>"
        "🔄 <strong style='color:#a0aac0;'>Keep Setup &amp; Start Over</strong> — "
        "use this if you are continuing with the same gameplay section. "
        "Your gameplay type, start condition, success condition, failure condition and end condition "
        "will all be kept exactly as they are, so you don't have to re-enter them. "
        "Only the analysis results are cleared."
        "</p>"
        "<p style='font-family:Share Tech Mono,monospace; font-size:0.75rem; "
        "color:#7080a0; margin:0;'>"
        "✨ <strong style='color:#a0aac0;'>Start Fresh</strong> — "
        "use this if you are moving to a different gameplay section, level, layout, or encounter. "
        "Everything is cleared including the gameplay type and conditions, "
        "so you can describe the new section from scratch."
        "</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-top:14px;'>", unsafe_allow_html=True)
    sec5_col1, sec5_col2 = st.columns(2)
    with sec5_col1:
        if st.button("🔄 Keep Setup & Start Over", key="s5_keep_btn"):
            st.session_state["_instance_counter"] += 1
            for key in [
                "_analysis_complete", "_result", "_analysis", "_recommendations",
                "_followup_complete", "_followup_result", "_followup_analysis",
                "_followup_recommendations", "_followup_file_bytes", "applied_recs",
                "session_id", "current_iteration",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["_reset_note"] = "keep"
            st.rerun()
    with sec5_col2:
        if st.button("✨ Start Fresh", key="s5_fresh_btn"):
            st.session_state["_instance_counter"] += 1
            for key in [
                "_analysis_complete", "_result", "_analysis", "_recommendations",
                "_followup_complete", "_followup_result", "_followup_analysis",
                "_followup_recommendations", "_followup_file_bytes", "applied_recs",
                "session_id", "current_iteration",
                "_family_idx_saved", "_start_cond", "_end_cond",
                "_success_cond", "_failure_cond",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["_reset_note"] = "fresh"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# SECTION 6 — Leave a Review
# ---------------------------------------------------------------------------
st.header("06 // LEAVE A REVIEW")

_review_iteration = st.session_state.get("current_iteration", 1)
st.markdown(
    f"<p style='font-family:Share Tech Mono,monospace; font-size:0.78rem; color:#8090c0; "
    f"margin-bottom:16px;'>"
    f"Help us improve the tool. This review is for <strong>iteration {_review_iteration}</strong> — "
    f"rate your experience and/or leave a written comment below."
    f"</p>",
    unsafe_allow_html=True,
)

with st.expander("💬 What the ratings and review are asking", expanded=False):
    st.markdown(
        "- Was the tool easy to understand?\n"
        "- Was the workflow clear?\n"
        "- Were the recommendations helpful?\n"
        "- Were the explanations understandable?\n"
        "- Were the suggestions too vague or too specific?\n"
        "- Did the tool feel implementable in your development process?\n"
        "- What confused you?\n"
        "- What would you improve?"
    )

st.markdown(
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.80rem; color:#ffe066; "
    "margin-bottom:4px; margin-top:10px;'>Rate your experience (1 = strongly disagree, 5 = strongly agree)</p>",
    unsafe_allow_html=True,
)

# Widget keys include the iteration number so ratings don't carry over
# stale defaults from a previous iteration's review.
_rk = lambda name: f"rating_{name}_iter{_review_iteration}"

rating_clarity = st.radio(
    "The workflow was clear and easy to follow.",
    [1, 2, 3, 4, 5], index=None, horizontal=True, key=_rk("clarity"),
)
rating_recommendation_quality = st.radio(
    "The recommendations felt useful and actionable.",
    [1, 2, 3, 4, 5], index=None, horizontal=True, key=_rk("recommendation_quality"),
)
rating_explainability = st.radio(
    "The explanations (why a recommendation was made) were understandable.",
    [1, 2, 3, 4, 5], index=None, horizontal=True, key=_rk("explainability"),
)
rating_implementability = st.radio(
    "I could see myself actually applying these suggestions in development.",
    [1, 2, 3, 4, 5], index=None, horizontal=True, key=_rk("implementability"),
)
rating_overall = st.radio(
    "Overall, I would use this tool again.",
    [1, 2, 3, 4, 5], index=None, horizontal=True, key=_rk("overall"),
)

st.markdown(
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.80rem; color:#ffe066; "
    "margin-bottom:4px; margin-top:14px;'>Anything else you'd like to share?</p>",
    unsafe_allow_html=True,
)
review_text = st.text_area(
    "Your review",
    placeholder="Share your thoughts about the tool...",
    height=160,
    key=f"review_text_iter{_review_iteration}",
    label_visibility="collapsed",
)

st.markdown(
    "<p style='font-family:Share Tech Mono,monospace; font-size:0.72rem; color:#506080; "
    "margin-top:6px;'>"
    "🔒 Uploaded files and reviews may be stored locally for tool improvement and "
    "evaluation purposes. No personal data such as IP address or user identity is collected. "
    "Please avoid including your name or contact details in the written review."
    "</p>",
    unsafe_allow_html=True,
)

if st.button("📨 SUBMIT REVIEW", type="primary"):
    _ratings_given = [r for r in [
        rating_clarity, rating_recommendation_quality, rating_explainability,
        rating_implementability, rating_overall,
    ] if r is not None]
    if not _ratings_given and not review_text.strip():
        st.warning("⚠️ Please provide at least one rating or a written comment before submitting.")
    else:
        try:
            _payload = {
                "review_text":                    review_text.strip(),
                "gameplay_type":                   telemetry_family,
                "instance_id":                     instance_id,
                "session_id":                      st.session_state.get("session_id", ""),
                "iteration_number":                _review_iteration,
                "rating_clarity":                  rating_clarity,
                "rating_recommendation_quality":   rating_recommendation_quality,
                "rating_explainability":           rating_explainability,
                "rating_implementability":         rating_implementability,
                "rating_overall":                  rating_overall,
            }
            # requests would otherwise serialize None as the literal string
            # "None"; drop unanswered ratings so FastAPI's Form(None) default applies.
            _payload = {k: v for k, v in _payload.items() if v is not None}
            review_resp = requests.post(
                f"{API_BASE}/review",
                data=_payload,
                timeout=10,
            )
            if review_resp.status_code == 200:
                st.success("✅ Review submitted. Thank you for your feedback!")
            else:
                st.error("⚠️ Could not save review. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("⚠️ Cannot reach API. Make sure `python run.py` is running.")
        except Exception as e:
            st.error(f"Request failed: {e}")