"""
api/main.py
i-Game Game Balance Tool 1.0

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from core.parser import parse_upload
from core.validator import validate_events, dataset_warnings
from core.registry import get_family, list_families
from analysis.analyze import run_pipeline
from analysis.recommend import build_recommendations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="i-Game Game Balance Tool",
    version="1.0.0",
    description=(
        "Analyses gameplay telemetry and returns prioritised, explainable design recommendations. "
        "Supports iterative balancing sessions across five gameplay data types."
    ),
)

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

SESSIONS_DIR       = Path(os.getenv("SESSIONS_DIR",       str(_PROJECT_ROOT / "data" / "balancing_sessions")))

# ---------------------------------------------------------------------------
# General persistence helpers
# ---------------------------------------------------------------------------

def _sanitize(value: str, max_len: int = 40) -> str:
    sanitized = re.sub(r"[^\w\-]", "_", value)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:max_len]


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
    if val_errors:
        analysis.setdefault("warnings", []).append(
            f"INVALID_EVENTS|Skipped {len(val_errors)} event(s) that failed validation.")
        analysis["warnings"].extend(val_errors[:5])
    analysis.setdefault("warnings", []).extend(dataset_warnings(gi_dict, clean_events))
    return {"status": "ok", "family": fam_name, "analysis": analysis, "recommendations": recs}


# ---------------------------------------------------------------------------
# POST /analyze  — main analysis endpoint, auto-creates balancing session
# ---------------------------------------------------------------------------

@app.post("/analyze", summary="Analyze a gameplay instance")
async def analyze(
    file: UploadFile = File(...),
    game_name: str = Form(""),
) -> JSONResponse:
    raw = await file.read()

    # Parse
    try:
        gi_dict, events = parse_upload(raw)
    except ValueError as exc:
        return JSONResponse(status_code=422, content={
            "status": "error", "family": "", "analysis": None,
            "recommendations": [],
            "session_id": None, "errors": [str(exc)]})

    family_name = gi_dict.get("telemetry_family", "game_jam_generic")
    instance_id = gi_dict.get("instance_id", "")

    # Resolve family
    try:
        family = get_family(family_name)
    except ValueError as exc:
        return JSONResponse(status_code=422, content={
            "status": "error", "family": family_name, "analysis": None,
            "recommendations": [],
            "session_id": None, "errors": [str(exc)]})

    # Validate
    clean_events, val_errors = validate_events(
        events, family["required_fields"], family["optional_defaults"])
    if not clean_events:
        return JSONResponse(status_code=422, content={
            "status": "error", "family": family_name, "analysis": None,
            "recommendations": [],
            "session_id": None,
            "errors": val_errors or ["No valid events after validation."]})

    # Extract
    try:
        sessions_df = family["extract"](clean_events)
    except Exception as exc:
        logger.exception("Feature extraction failed.")
        return JSONResponse(status_code=500, content={
            "status": "error", "family": family_name, "analysis": None,
            "recommendations": [],
            "session_id": None, "errors": [f"Feature extraction failed: {exc}"]})

    # Pipeline
    try:
        analysis_dict = run_pipeline(
            sessions_df, feature_cols=family["feature_cols"],
            use_shap=True, top_k=5)
    except Exception as exc:
        logger.exception("Analysis pipeline failed.")
        return JSONResponse(status_code=500, content={
            "status": "error", "family": family_name, "analysis": None,
            "recommendations": [],
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
             f"Common causes: a required field is missing or null, a value has the wrong type "
             f"or is out of range (e.g. success_flag must be 0 or 1), or values contradict each other. "
             f"Check all fields for the '{family_name}' gameplay type."]
            + val_errors[:5])

    # Dataset-level checks: missing gameplay_instance, constant-zero
    # measurement fields, session_id shared by several players
    extra_warnings = dataset_warnings(gi_dict, clean_events)
    if extra_warnings:
        analysis_dict.setdefault("warnings", []).extend(extra_warnings)

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

    response_body = {
        "status":          "ok",
        "family":          family_name,
        "analysis":        analysis_dict,
        "recommendations": recommendations,
        "session_id":      session_id or None,
        "errors":          [],
    }

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
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}
