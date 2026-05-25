"""Pydantic schemas for the production companion service."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ──

class Intent(str, Enum):
    MEAL_PREDICTION = "meal_prediction"
    HISTORY_COMPARE = "history_compare"
    RISK_CHECK = "risk_check"
    FOOD_LOG = "food_log"
    WATCH_PLAN = "watch_plan"


class Trend(str, Enum):
    RISING = "rising"
    STEADY = "steady"
    FALLING = "falling"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class AnchorType(str, Enum):
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


# ── Request models ──

class GlucoseContext(BaseModel):
    """Current CGM reading and context for the user."""
    current_glucose_mg_dl: float = Field(..., ge=40, le=400, description="Current CGM reading in mg/dL")
    trend: Trend = Field(default=Trend.STEADY, description="Glucose trend arrow")
    sensor_lag_minutes: int = Field(default=15, ge=5, le=30, description="CGM sensor lag")
    insulin_on_board_units: float = Field(default=0.0, ge=0, le=50, description="Active insulin on board")
    recent_meal: Optional[str] = Field(default=None, description="Most recent meal food name")
    recent_meal_time: Optional[datetime] = Field(default=None, description="When the recent meal was eaten")
    activity_level: str = Field(default="normal", pattern=r"^(low|normal|high)$")


class CompanionRequest(BaseModel):
    """Single consolidated request to the companion service."""
    scenario: str = Field(..., min_length=1, max_length=2000, description="Raw free-text meal description")
    user_id: str = Field(..., min_length=1, max_length=100, description="User identifier")
    intent: Intent = Field(default=Intent.MEAL_PREDICTION, description="Question intent")
    glucose_context: Optional[GlucoseContext] = Field(default=None, description="Current CGM context")
    anchor_type: Optional[AnchorType] = Field(default=None, description="Override anchor selection")
    request_id: str = Field(default="", description="Correlation ID for tracing")

    @field_validator("scenario")
    @classmethod
    def scenario_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 2:
            raise ValueError("Scenario must be at least 2 characters")
        return stripped


# ── Response models ──

class ParsedFoodItem(BaseModel):
    """A single food item parsed from the scenario."""
    item: str = Field(..., description="Clean food name")
    quantity: float = Field(default=1.0, ge=0.1, description="Quantity")
    unit: Optional[str] = Field(default=None, description="Unit of measure")
    serving_grams: Optional[float] = Field(default=None, description="Estimated serving weight in grams")


class DatabaseMatch(BaseModel):
    """A food database match result."""
    food_name: str = Field(..., description="Original food name")
    matched_name: Optional[str] = Field(default=None, description="Database product name")
    matched_brand: Optional[str] = Field(default=None, description="Database product brand")
    barcode: Optional[str] = Field(default=None, description="Product barcode")
    carbs_per_100g: Optional[float] = Field(default=None)
    fat_per_100g: Optional[float] = Field(default=None)
    protein_per_100g: Optional[float] = Field(default=None)
    kcal_per_100g: Optional[float] = Field(default=None)
    serving_grams: Optional[float] = Field(default=None)
    computed_carbs_g: Optional[float] = Field(default=None)
    computed_fat_g: Optional[float] = Field(default=None)
    computed_protein_g: Optional[float] = Field(default=None)
    computed_kcal: Optional[float] = Field(default=None)
    confidence: Confidence = Field(default=Confidence.MEDIUM)


class HistoricalMeal(BaseModel):
    """A historical meal from the user's history."""
    food: str
    date: Optional[str] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    peak_delta_mg_dl: Optional[float] = None
    peak_time_minutes: Optional[float] = None
    confidence_score: Optional[float] = None


class ForecastPoint(BaseModel):
    hour: int = Field(..., ge=1, le=24)
    glucose_mg_dl: int = Field(..., ge=40, le=400)


class NighttimePoint(BaseModel):
    time: str
    hours_after_meal: int = Field(..., ge=6, le=16)
    glucose_mg_dl: int = Field(..., ge=40, le=400)
    note: str = ""


class Forecast(BaseModel):
    baseline_mg_dl: int
    peak_mg_dl: int
    peak_time_minutes: int
    forecast_points: list[ForecastPoint] = Field(default_factory=list)
    nighttime: list[NighttimePoint] = Field(default_factory=list)
    exercise_heat_modifier: float = 1.0


class SimUserProfile(BaseModel):
    """The simulated user profile used for this request."""
    anchor_type: str
    label: str
    description: str
    basal_glucose_mg_dl: float
    carb_ratio: float
    insulin_sensitivity: float
    fat_delay_hours: float
    exercise_drop_factor: float
    hypo_risk: float


class CompanionResponse(BaseModel):
    """Final response to the user."""
    request_id: str
    sim_profile: SimUserProfile
    current_glucose_mg_dl: int
    trend: str
    insulin_on_board_units: float
    parsed_foods: list[ParsedFoodItem] = Field(default_factory=list)
    database_matches: list[DatabaseMatch] = Field(default_factory=list)
    meal_totals: dict[str, float] = Field(default_factory=dict)
    educational_bolus_estimate_units: Optional[float] = None
    forecast: Optional[Forecast] = None
    historical_meals: list[HistoricalMeal] = Field(default_factory=list)
    companion_advice: str = ""
    safety_check: str = "passed"
    processing_time_ms: float = 0.0