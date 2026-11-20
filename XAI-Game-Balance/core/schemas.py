"""
core/schemas.py
Pydantic models for Game Balance Tool v1.3 — Game Jam Edition.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GameplayInstance(BaseModel):
    instance_id: str
    start_condition: str = ""
    end_condition: str = ""
    success_condition: str = ""
    failure_condition: str = ""
    telemetry_family: str = "pathfinding"


class AnalyzeV2Request(BaseModel):
    gameplay_instance: GameplayInstance
    events: List[Dict[str, Any]]


class FeatureImportanceEntry(BaseModel):
    feature: str
    importance: float


class Recommendation(BaseModel):
    level_id: str
    problem: str
    technical_reason: str
    suggestion: str
    expected_impact: str
    priority: str  # "high" | "medium" | "low"


class LevelSummary(BaseModel):
    level_id: str
    n_sessions: int
    success_rate: float
    mean_predicted_success: Optional[float] = None


class PerAgentSummary(BaseModel):
    player_id: str
    n_sessions: int
    success_rate: float
    mean_decision_time_ms: float
    retry_count: float


class Analysis(BaseModel):
    n_sessions: int
    n_levels: int
    n_agents: int
    overall_success_rate: float
    levels_by_difficulty: List[LevelSummary]
    per_level: Dict[str, Any]
    per_agent: List[PerAgentSummary]
    feature_importances: List[FeatureImportanceEntry]
    xai_method: str
    warnings: List[str] = Field(default_factory=list)


class AnalyzeV2Response(BaseModel):
    status: str
    family: str
    analysis: Optional[Analysis] = None
    recommendations: List[Recommendation] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
