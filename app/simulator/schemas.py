"""Pydantic schemas for the simulator domain."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    """Categories of synthetic events a simulator can generate."""
    MEAL = "meal"
    INSULIN = "insulin"
    EXERCISE = "exercise"
    SLEEP = "sleep"
    ILLNESS = "illness"
    ALCOHOL = "alcohol"
    STRESS = "stress"


class AnchorType(str, Enum):
    """The 12 anchor profile types."""
    WELL_CONTROLLED = "well_controlled"
    BRITTLE = "brittle"
    DAWN_PHENOMENON = "dawn_phenomenon"
    POST_MEAL_SPIKE = "post_meal_spike"
    OVERNIGHT_HYPO = "overnight_hypo"
    EXERCISE_SENSITIVE = "exercise_sensitive"
    HIGH_FAT_DELAYED = "high_fat_delayed"
    INSULIN_SENSITIVE = "insulin_sensitive"
    INSULIN_RESISTANT = "insulin_resistant"
    HIGH_VARIABILITY = "high_variability"
    EXERCISE_REGIMEN = "exercise_regimen"
    NEWLY_DIAGNOSED = "newly_diagnosed"


class RunStatus(str, Enum):
    """Simulation run lifecycle status."""
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Profile & Anchors ──


class AnchorProfile(BaseModel):
    """Definition of a single anchor profile with parameter ranges."""
    type: AnchorType
    label: str = Field(..., description="Human-readable label")
    description: str = Field(..., description="Profile description")


class AnchorParameterRange(BaseModel):
    """Parameter range for a specific anchor type."""
    anchor_type: AnchorType
    basal_glucose_mean: tuple[float, float] = Field(..., description="(min, max) for basal glucose in mg/dL")
    basal_glucose_amplitude: tuple[float, float] = Field(..., description="(min, max) circadian amplitude")
    meal_rise_factor: tuple[float, float] = Field(..., description="(min, max) glucose rise per g carb")
    insulin_sensitivity: tuple[float, float] = Field(..., description="(min, max) mg/dL drop per insulin unit")
    carb_ratio: tuple[float, float] = Field(..., description="(min, max) grams per insulin unit")
    hypo_risk: tuple[float, float] = Field(..., description="(min, max) 0-1 probability of hypo event")
    noise_sd: tuple[float, float] = Field(..., description="(min, max) glucose noise std dev")
    exercise_drop_factor: tuple[float, float] = Field(..., description="(min, max) glucose drop per exercise minute")
    dawn_effect_strength: tuple[float, float] = Field(..., description="(min, max) dawn phenomenon rise mg/dL")
    fat_delay_hours: tuple[float, float] = Field(..., description="(min, max) delayed spike window")
    variability_cv: tuple[float, float] = Field(..., description="(min, max) coefficient of variation %")


class PatientConfig(BaseModel):
    """Generated parameter set for a single synthetic patient."""
    anchor_type: AnchorType
    seed: int = Field(..., description="RNG seed for reproducibility")
    basal_glucose_mean: float = Field(..., description="Basal glucose mean mg/dL", ge=80, le=220)
    basal_glucose_amplitude: float = Field(..., description="Circadian amplitude mg/dL", ge=0, le=40)
    meal_rise_factor: float = Field(..., description="mg/dL rise per g carb", ge=0.5, le=8.0)
    insulin_sensitivity: float = Field(..., description="mg/dL drop per insulin unit", ge=10, le=80)
    carb_ratio: float = Field(..., description="grams per insulin unit", ge=5, le=30)
    hypo_risk: float = Field(..., description="Probability 0-1", ge=0, le=1)
    noise_sd: float = Field(..., description="Glucose noise std dev mg/dL", ge=2, le=30)
    exercise_drop_factor: float = Field(..., description="Drop per exercise minute", ge=0.5, le=5.0)
    dawn_effect_strength: float = Field(..., description="Dawn rise mg/dL", ge=0, le=60)
    fat_delay_hours: float = Field(..., description="Delayed spike window", ge=0, le=8)
    variability_cv: float = Field(..., description="CV percentage", ge=10, le=60)

    model_config = {"frozen": True}


# ── Simulation Run ──


class SimRunCreate(BaseModel):
    """Request to create and optionally start a simulation run."""
    name: str = Field(..., min_length=1, max_length=255, description="Run name")
    description: Optional[str] = Field(None, description="Description")
    anchor_count: int = Field(12, ge=1, le=20, description="Number of anchor profiles to use")
    users_per_anchor: int = Field(20, ge=1, le=100, description="Patients per anchor")
    days_per_user: int = Field(90, ge=7, le=365, description="Days of synthetic data per patient")
    config_json: Optional[dict[str, Any]] = Field(None, description="Additional run config")


class SimRunResponse(BaseModel):
    """Simulation run response."""
    id: int
    name: str
    description: Optional[str]
    status: str
    anchor_count: int
    users_per_anchor: int
    days_per_user: int
    config_json: Optional[dict[str, Any]]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    summary_json: Optional[dict[str, Any]]
    notes: Optional[str]
    created_by: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class SimRunListResponse(BaseModel):
    """List of simulation runs."""
    runs: list[SimRunResponse]
    total: int


class SimUserResponse(BaseModel):
    """Simulation user response."""
    id: int
    sim_run_id: int
    sim_user_key: str
    anchor_type: str
    real_user_id: Optional[int]
    parameter_json: Optional[dict[str, Any]]
    profile_json: Optional[dict[str, Any]]
    seed: Optional[int]

    model_config = {"from_attributes": True}


# ── Evaluation ──


class HiddenTruthResponse(BaseModel):
    """Hidden truth label response."""
    id: int
    sim_run_id: int
    sim_user_id: int
    pattern_type: str
    subtype: Optional[str]
    source_metric_id: Optional[int]
    target_metric_id: Optional[int]
    window_start: Optional[datetime]
    window_end: Optional[datetime]
    expected_peak_delta: Optional[float]
    expected_time_to_peak_min: Optional[float]
    expected_value_min: Optional[float]
    expected_value_max: Optional[float]
    truth_payload: Optional[dict[str, Any]]
    is_detected: Optional[bool]
    detector_confidence: Optional[float]

    model_config = {"from_attributes": True}


class DetectorScoreResponse(BaseModel):
    """Detector benchmark score."""
    id: int
    sim_run_id: int
    sim_user_id: Optional[int]
    detector_name: str
    detector_version: str
    anchor_type: Optional[str]
    pattern_type: Optional[str]
    metric_name: str
    metric_value: float
    breakdown_json: Optional[dict[str, Any]]

    model_config = {"from_attributes": True}


class EvaluationSummary(BaseModel):
    """Aggregated evaluation results for a run."""
    run_id: int
    run_name: str
    status: str
    total_truths: int
    truths_detected: int
    truths_missed: int
    detection_rate: float = Field(..., description="TP / (TP + FN)")
    avg_confidence_detected: float
    by_pattern_type: dict[str, dict[str, Any]]
    by_anchor_type: dict[str, dict[str, Any]]
    detector_scores: dict[str, float]
    calibration: Optional[dict[str, Any]] = Field(
        None,
        description="Confidence calibration analysis: ECE, per-bin accuracy, threshold recommendations"
    )
    disclaimer: str = Field(
        default="Evaluation results are for benchmarking pattern detection "
                "on synthetic data. They do not represent clinical outcomes."
    )
