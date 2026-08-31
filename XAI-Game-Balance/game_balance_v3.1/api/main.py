"""
api/main.py
Game Balance Tool v3.2

Endpoints
---------
POST /analyze                           Upload + run pipeline + auto-create balancing session
POST /session/{session_id}/iteration    Upload next iteration JSON, saves upload + result + applied recs
POST /session/{session_id}/applied      Save applied recommendations for transition into next iteration
GET  /session/{session_id}              Return session metadata + iteration summary
GET  /families                          List registered families
GET  /health                            Health check

Persistence layout
------------------
data/uploads/                           Raw uploads from /analyze (legacy, kept for compatibility)
data/results/                           Results from /analyze (legacy)
data/logs/usage.jsonl                   One line per /analyze request
data/logs/reviews.jsonl                 User feedback reviews
data/balancing_sessions/session_<id>/   One folder per balancing session
    metadata.json
    iteration_01_upload.json
    iteration_01_result.json
    iteration_02_applied_recommendations.json
    iteration_02_upload.json
    iteration_02_result.json
    ...
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from core.parser import parse_upload
from core.validator import validate_events
from core.registry import get_family, list_families
from analysis.analyze import run_pipeline
from analysis.recommend import build_recommendations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Game Balance Tool v3.2",
    version="3.2.0",
    description=(
        "v3.2: balancing sessions, iteration tracking, applied recommendations comparison. "
        "Multi-family telemetry analysis with generic gameplay variables."
    ),
)

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

UPLOAD_SAVE_DIR    = Path(os.getenv("UPLOAD_SAVE_DIR",    str(_PROJECT_ROOT / "data" / "uploads")))
RESULTS_SAVE_DIR   = Path(os.getenv("RESULTS_SAVE_DIR",   str(_PROJECT_ROOT / "data" / "results")))
LOGS_DIR           = Path(os.getenv("LOGS_DIR",           str(_PROJECT_ROOT / "data" / "logs")))
SESSIONS_DIR       = Path(os.getenv("SESSIONS_DIR",       str(_PROJECT_ROOT / "data" / "balancing_sessions")))
USAGE_LOG_PATH     = LOGS_DIR / "usage.jsonl"
REVIEWS_LOG_PATH   = LOGS_DIR / "reviews.jsonl"

# ---------------------------------------------------------------------------
# General persistence helpers
# ---------------------------------------------------------------------------

def _sanitize(value: str, max_len: int = 40) -> str:
    sanitized = re.sub(r"[^\w\-]", "_", value)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:max_len]


def _build_base_filename(family_name: str, instance_id: str) -> str:
    ts        = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    fam_safe  = _sanitize(family_name)
    inst_safe = _sanitize(instance_id) if instance_id else "unknown"
    short_id  = uuid.uuid4().hex[:4]
    return f"{ts}_{fam_safe}_{inst_safe}_{short_id}"


def _save_upload(raw: bytes, base_filename: str) -> str:
    try:
        UPLOAD_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        filename  = f"{base_filename}.json"
        (UPLOAD_SAVE_DIR / filename).write_bytes(raw)
        logger.info("Upload saved: %s", filename)
        return filename
    except Exception as exc:
        logger.warning("Could not save upload: %s", exc)
        return ""


def _save_result(result: dict, base_filename: str, target_dir: Path | None = None) -> str:
    try:
        save_dir = target_dir or RESULTS_SAVE_DIR
        save_dir.mkdir(parents=True, exist_ok=True)
        filename  = f"{base_filename}_result.json"
        (save_dir / filename).write_text(json.dumps(result, indent=2), encoding="utf-8")
        logger.info("Result saved: %s", filename)
        return filename
    except Exception as exc:
        logger.warning("Could not save result: %s", exc)
        return ""


def _log_usage(*, timestamp, family_name, instance_id, n_events,
               n_sessions, status, saved_upload, error_message=None) -> None:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp":             timestamp,
            "gameplay_type":         family_name,
            "instance_id":           instance_id or None,
            "n_events":              n_events,
            "n_sessions":            n_sessions,
            "status":                status,
            "saved_upload_filename": saved_upload or None,
            "error_message":         error_message,
        }
        with USAGE_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("Could not write usage log: %s", exc)


# ---------------------------------------------------------------------------
# Balancing session helpers
# ---------------------------------------------------------------------------

def _session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / f"session_{session_id}"


def _create_session(session_id: str, family_name: str, instance_id: str) -> Path:
    """Create session folder and write metadata.json. Returns session dir."""
    sdir = _session_dir(session_id)
    sdir.mkdir(parents=True, exist_ok=True)
    meta = {
        "session_id":   session_id,
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "gameplay_type": family_name,
        "instance_id":  instance_id or None,
        "iterations":   [],
    }
    (sdir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return sdir


def _load_session_meta(session_id: str) -> dict | None:
    meta_path = _session_dir(session_id) / "metadata.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _update_session_meta(session_id: str, iteration_number: int,
                         upload_file: str, result_file: str,
                         original_filename: str = "") -> None:
    meta = _load_session_meta(session_id)
    if not meta:
        return
    meta["iterations"].append({
        "iteration_number":  iteration_number,
        "upload_file":       upload_file,
        "original_filename": original_filename or None,
        "result_file":       result_file,
        "timestamp":         datetime.now(timezone.utc).isoformat(),
    })
    sdir = _session_dir(session_id)
    (sdir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _run_analysis_pipeline(raw: bytes, family_name: str) -> dict:
    """Parse → validate → extract → pipeline → recommend. Returns full response dict."""
    gi_dict, events = parse_upload(raw)
    fam_name = gi_dict.get("telemetry_family", family_name)
    family   = get_family(fam_name)
    clean_events, val_errors = validate_events(
        events, family["required_fields"], family["optional_defaults"]
    )
    if not clean_events:
        raise ValueError(f"No valid events after validation: {val_errors[:3]}")
    sessions_df  = family["extract"](clean_events)
    analysis     = run_pipeline(sessions_df, feature_cols=family["feature_cols"],
                                use_shap=True, top_k=5)
    sessions_df2 = analysis.pop("_sessions_df")
    recs         = build_recommendations(sessions_df2, analysis["per_level"], family["rules"])
    return {"status": "ok", "family": fam_name, "analysis": analysis, "recommendations": recs}


# ---------------------------------------------------------------------------
# POST /analyze  — main analysis endpoint, auto-creates balancing session
# ---------------------------------------------------------------------------

@app.post("/analyze", summary="Analyze a gameplay instance")
async def analyze(
    file: UploadFile = File(...),
    game_name: str = Form(""),
) -> JSONResponse:
    raw       = await file.read()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

    # Parse
    try:
        gi_dict, events = parse_upload(raw)
    except ValueError as exc:
        _log_usage(timestamp=timestamp, family_name="", instance_id="",
                   n_events=None, n_sessions=None, status="error",
                   saved_upload="", error_message=str(exc))
        return JSONResponse(status_code=422, content={
            "status": "error", "family": "", "analysis": None,
            "recommendations": [], "saved_file": None,
            "session_id": None, "errors": [str(exc)]})

    family_name = gi_dict.get("telemetry_family", "game_jam_generic")
    instance_id = gi_dict.get("instance_id", "")
    n_events    = len(events)

    # Save raw upload
    base_filename = _build_base_filename(family_name, instance_id)
    saved_upload  = _save_upload(raw, base_filename)

    # Resolve family
    try:
        family = get_family(family_name)
    except ValueError as exc:
        _log_usage(timestamp=timestamp, family_name=family_name,
                   instance_id=instance_id, n_events=n_events,
                   n_sessions=None, status="error",
                   saved_upload=saved_upload, error_message=str(exc))
        return JSONResponse(status_code=422, content={
            "status": "error", "family": family_name, "analysis": None,
            "recommendations": [], "saved_file": saved_upload or None,
            "session_id": None, "errors": [str(exc)]})

    # Validate
    clean_events, val_errors = validate_events(
        events, family["required_fields"], family["optional_defaults"])
    if not clean_events:
        _log_usage(timestamp=timestamp, family_name=family_name,
                   instance_id=instance_id, n_events=n_events,
                   n_sessions=None, status="error", saved_upload=saved_upload,
                   error_message="; ".join(val_errors[:3]))
        return JSONResponse(status_code=422, content={
            "status": "error", "family": family_name, "analysis": None,
            "recommendations": [], "saved_file": saved_upload or None,
            "session_id": None,
            "errors": val_errors or ["No valid events after validation."]})

    # Extract
    try:
        sessions_df = family["extract"](clean_events)
    except Exception as exc:
        logger.exception("Feature extraction failed.")
        _log_usage(timestamp=timestamp, family_name=family_name,
                   instance_id=instance_id, n_events=n_events,
                   n_sessions=None, status="error", saved_upload=saved_upload,
                   error_message=f"Feature extraction failed: {exc}")
        return JSONResponse(status_code=500, content={
            "status": "error", "family": family_name, "analysis": None,
            "recommendations": [], "saved_file": saved_upload or None,
            "session_id": None, "errors": [f"Feature extraction failed: {exc}"]})

    n_sessions = int(len(sessions_df))

    # Pipeline
    try:
        analysis_dict = run_pipeline(
            sessions_df, feature_cols=family["feature_cols"],
            use_shap=True, top_k=5)
    except Exception as exc:
        logger.exception("Analysis pipeline failed.")
        _log_usage(timestamp=timestamp, family_name=family_name,
                   instance_id=instance_id, n_events=n_events,
                   n_sessions=n_sessions, status="error",
                   saved_upload=saved_upload, error_message=f"Analysis failed: {exc}")
        return JSONResponse(status_code=500, content={
            "status": "error", "family": family_name, "analysis": None,
            "recommendations": [], "saved_file": saved_upload or None,
            "session_id": None, "errors": [f"Analysis failed: {exc}"]})

    # Recommendations
    pipeline_sessions_df = analysis_dict.pop("_sessions_df")
    try:
        recommendations = build_recommendations(
            pipeline_sessions_df, analysis_dict["per_level"], family["rules"])
    except Exception as exc:
        logger.exception("Recommendation generation failed.")
        recommendations = []
        analysis_dict.setdefault("warnings", []).append(
            f"RECOMMENDATION_FAILED|"
            f"The recommendation engine encountered an error: {exc}. "
            f"The analysis data above is still valid. "
            f"Check that your events contain the required fields for the selected gameplay type "
            f"and that at least one level_end event exists per session.")

    if val_errors:
        analysis_dict.setdefault("warnings", []).extend(
            [f"INVALID_EVENTS|Skipped {len(val_errors)} event(s) that failed validation. "
             f"Common causes: a required field is missing or null. "
             f"Check all required fields for the '{family_name}' gameplay type."]
            + val_errors[:5])

    # Session ID format: <sanitized_game_name>_<instance_counter>_DDMMYY_HHMMSS
    _ts_session  = datetime.now(timezone.utc)
    _game_safe   = _sanitize(game_name.strip()) if game_name.strip() else _sanitize(family_name)
    _inst_safe   = _sanitize(instance_id.strip()) if instance_id.strip() else "001"
    # Extract just the counter part from instance_id (e.g. "ant_colony_001" → "001")
    _counter_part = _inst_safe.split("_")[-1] if "_" in _inst_safe else _inst_safe
    session_id   = f"{_game_safe}_{_counter_part}_{_ts_session.strftime('%d%m%y_%H%M%S')}"
    try:
        sdir = _create_session(session_id, family_name, instance_id)
        (sdir / "iteration_01_upload.json").write_bytes(raw)
        result_body = {
            "status": "ok", "family": family_name,
            "analysis": analysis_dict, "recommendations": recommendations
        }
        (sdir / "iteration_01_result.json").write_text(
            json.dumps(result_body, indent=2), encoding="utf-8")
        _update_session_meta(session_id, 1,
                             "iteration_01_upload.json",
                             "iteration_01_result.json",
                             original_filename=file.filename or "")
        logger.info("Balancing session created: session_%s", session_id)
    except Exception as exc:
        logger.warning("Could not create balancing session: %s", exc)
        session_id = ""

    # Save to legacy locations + log
    response_body = {
        "status":          "ok",
        "family":          family_name,
        "analysis":        analysis_dict,
        "recommendations": recommendations,
        "saved_file":      saved_upload or None,
        "session_id":      session_id or None,
        "errors":          [],
    }
    _save_result(response_body, base_filename)
    _log_usage(timestamp=timestamp, family_name=family_name,
               instance_id=instance_id, n_events=n_events,
               n_sessions=n_sessions, status="ok",
               saved_upload=saved_upload)

    return JSONResponse(content=response_body)


# ---------------------------------------------------------------------------
# POST /session/{session_id}/iteration  — upload next iteration
# ---------------------------------------------------------------------------

@app.post("/session/{session_id}/iteration",
          summary="Upload next iteration JSON for a balancing session")
async def session_iteration(
    session_id: str,
    file: UploadFile = File(...),
    iteration_number: int = Form(...),
    gameplay_type: str = Form(""),
) -> JSONResponse:
    raw = await file.read()

    meta = _load_session_meta(session_id)
    if not meta:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "errors": [f"Session '{session_id}' not found."]})

    sdir         = _session_dir(session_id)
    iter_pad     = f"{iteration_number:02d}"
    upload_name  = f"iteration_{iter_pad}_upload.json"
    result_name  = f"iteration_{iter_pad}_result.json"

    # Save upload
    try:
        (sdir / upload_name).write_bytes(raw)
    except Exception as exc:
        logger.warning("Could not save iteration upload: %s", exc)

    # Run analysis
    fam_name = meta.get("gameplay_type") or gameplay_type or "game_jam_generic"
    try:
        result_body = _run_analysis_pipeline(raw, fam_name)
        (sdir / result_name).write_text(
            json.dumps(result_body, indent=2), encoding="utf-8")
        _update_session_meta(session_id, iteration_number, upload_name, result_name,
                             original_filename=file.filename or "")
    except Exception as exc:
        logger.warning("Analysis failed for iteration %d: %s", iteration_number, exc)
        result_body = {"status": "error", "errors": [str(exc)],
                       "analysis": None, "recommendations": []}

    result_body["iteration_number"] = iteration_number
    result_body["session_id"]       = session_id
    return JSONResponse(content=result_body)


# ---------------------------------------------------------------------------
# POST /session/{session_id}/applied  — save applied recommendations
# ---------------------------------------------------------------------------

@app.post("/session/{session_id}/applied",
          summary="Save applied recommendations before uploading next iteration")
async def session_applied(
    session_id: str,
    next_iteration_number: int = Form(...),
    applied_recommendations: str = Form(...),  # JSON string
) -> JSONResponse:
    meta = _load_session_meta(session_id)
    if not meta:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "errors": [f"Session '{session_id}' not found."]})

    try:
        applied = json.loads(applied_recommendations)
    except Exception:
        return JSONResponse(status_code=422, content={
            "status": "error",
            "errors": ["applied_recommendations must be a valid JSON string."]})

    sdir     = _session_dir(session_id)
    iter_pad = f"{next_iteration_number:02d}"
    filename = f"iteration_{iter_pad}_applied_recommendations.json"

    try:
        payload = {
            "session_id":           session_id,
            "next_iteration":       next_iteration_number,
            "saved_at":             datetime.now(timezone.utc).isoformat(),
            "applied_recommendations": applied,
        }
        (sdir / filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Applied recs saved: %s / %s", session_id, filename)
    except Exception as exc:
        logger.warning("Could not save applied recommendations: %s", exc)
        return JSONResponse(status_code=500, content={
            "status": "error", "errors": [str(exc)]})

    return JSONResponse(content={"status": "ok", "saved_file": filename})


# ---------------------------------------------------------------------------
# GET /session/{session_id}  — return session metadata
# ---------------------------------------------------------------------------

@app.get("/session/{session_id}", summary="Get balancing session metadata")
def get_session(session_id: str) -> JSONResponse:
    meta = _load_session_meta(session_id)
    if not meta:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "errors": [f"Session '{session_id}' not found."]})
    return JSONResponse(content={"status": "ok", "session": meta})


# ---------------------------------------------------------------------------
# GET /families
# ---------------------------------------------------------------------------

@app.get("/families", summary="List registered telemetry families")
def get_families() -> JSONResponse:
    return JSONResponse(content={"families": list_families()})


# ---------------------------------------------------------------------------
# POST /review
# ---------------------------------------------------------------------------

@app.post("/review", summary="Save a user feedback review")
async def save_review(
    review_text: str = Form(""),
    gameplay_type: str = Form(""),
    instance_id: str = Form(""),
    session_id: str = Form(""),
    iteration_number: int | None = Form(None),
    rating_clarity: int | None = Form(None),
    rating_recommendation_quality: int | None = Form(None),
    rating_explainability: int | None = Form(None),
    rating_implementability: int | None = Form(None),
    rating_overall: int | None = Form(None),
) -> JSONResponse:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

    ratings = {
        "clarity":                 rating_clarity,
        "recommendation_quality":  rating_recommendation_quality,
        "explainability":          rating_explainability,
        "implementability":        rating_implementability,
        "overall":                 rating_overall,
    }
    # Clamp any provided rating to the valid 1-5 range defensively
    ratings = {k: (min(5, max(1, v)) if v is not None else None) for k, v in ratings.items()}
    has_ratings = any(v is not None for v in ratings.values())

    if not review_text.strip() and not has_ratings:
        return JSONResponse(status_code=422, content={
            "status": "error",
            "errors": ["Provide at least one rating or a written review."]})
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp":        timestamp,
            "gameplay_type":    gameplay_type or None,
            "instance_id":      instance_id or None,
            "session_id":       session_id or None,
            "iteration_number": iteration_number,
            "ratings":          ratings,
            "review":           review_text.strip() or None,
        }
        with REVIEWS_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        return JSONResponse(status_code=500, content={
            "status": "error", "errors": [str(exc)]})
    return JSONResponse(content={"status": "ok", "timestamp": timestamp})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok", "version": "3.2.0"}
