"""MealForecastRequest/Response — canonical typed API contract for meal forecasting.

This module defines the formal, versioned Pydantic schemas used by the
meal forecasting endpoint, persistence layer, and iOS/Flutter clients.

Version: 1.0.0

All downstream services and clients MUST depend on these schemas rather than
loose dicts or internal dataclasses. The dataclasses in
app/services/meal_forecast_engine.py remain the internal domain objects;
these schemas are the serialization/API boundary.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class RiskLevel(str, Enum):
    """Predicted glucose impact risk for a meal."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very-high"


class ConfidenceTier(str, Enum):
    """Confidence tier for a forecast value."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class MealType(str, Enum):
    """Standard meal type identifiers."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class SourceTrustTier(str, Enum):
    """Trust tier for food data sources — mirrors app.food.provenance."""
    VERIFIED = "verified"
    OFFICIAL = "official"
    COMMUNITY = "community"
    ESTIMATED = "estimated"


# ──────────────────────────────────────────────
# Request models
# ──────────────────────────────────────────────


class MealItemSchema(BaseModel):
    """A single food item in a meal forecast request.

    Items can be resolved by barcode, by free-text name, or by direct
    nutrient values for custom/user-defined foods.
    """

    name: str = Field(
        ..., max_length=255,
        description="Food item name (free text or display name).",
        examples=["Big Mac", "oatmeal", "grilled chicken salad"],
    )
    barcode: Optional[str] = Field(
        None, max_length=64,
        description="UPC/EAN barcode for precise Open Food Facts lookup.",
        examples=["5901234123457"],
    )
    quantity: float = Field(
        ..., gt=0,
        description="Quantity of this food item consumed.",
        examples=[1, 2, 0.5, 150],
    )
    unit: str = Field(
        default="serving",
        max_length=50,
        description="Unit of the quantity value (g, ml, serving, slice, piece, cup, oz, etc.).",
        examples=["serving", "g", "ml", "slices", "pieces"],
    )
    brand: Optional[str] = Field(
        None, max_length=255,
        description="Brand name for disambiguation.",
        examples=["McDonald's", "Quaker", "Kirkland"],
    )


class MealForecastRequest(BaseModel):
    """Request a meal glucose forecast.

    The canonical input contract for the meal forecasting feature.
    Clients (iOS, Flutter, web) should send this exact shape.
    """

    meal_items: list[MealItemSchema] = Field(
        ..., min_length=1, max_length=50,
        description="One or more food items that make up the meal.",
    )
    meal_timestamp: Optional[datetime] = Field(
        None,
        description="When the meal was/will-be eaten. Defaults to server time if omitted.",
        examples=["2026-05-21T12:30:00Z"],
    )
    timezone: Optional[str] = Field(
        None, max_length=64,
        description="IANA timezone string for the user's local time.",
        examples=["America/New_York", "Europe/London", "Asia/Tokyo"],
    )
    current_glucose: Optional[float] = Field(
        None, ge=20, le=600,
        description="Most recent CGM reading in mg/dL at time of request.",
        examples=[110, 145, 200],
    )
    meal_type: Optional[MealType] = Field(
        None,
        description="Meal type category for context-aware analysis.",
    )
    notes: Optional[str] = Field(
        None, max_length=500,
        description="Optional user notes or context for the meal.",
        examples=["Pre-workout meal", "Eating out — estimating portions"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal_items": [
                    {"name": "oatmeal", "quantity": 1, "unit": "serving", "barcode": "5901234123457"},
                    {"name": "banana", "quantity": 1, "unit": "medium", "barcode": "4012345678901"},
                    {"name": "honey", "quantity": 1, "unit": "tbsp"},
                ],
                "meal_timestamp": "2026-05-21T07:30:00Z",
                "timezone": "America/New_York",
                "current_glucose": 105,
                "meal_type": "breakfast",
            }
        },
    )

    @field_validator("meal_items")
    @classmethod
    def _validate_meal_items_not_empty(cls, v: list[MealItemSchema]) -> list[MealItemSchema]:
        if not v:
            raise ValueError("At least one meal item is required.")
        return v


# ──────────────────────────────────────────────
# Response models
# ──────────────────────────────────────────────


class NutrientTotals(BaseModel):
    """Aggregated nutrient totals for the meal (actual amounts, not per 100g)."""
    carbs_g: Optional[float] = Field(None, ge=0, description="Total carbohydrates in grams.")
    protein_g: Optional[float] = Field(None, ge=0, description="Total protein in grams.")
    fat_g: Optional[float] = Field(None, ge=0, description="Total fat in grams.")
    fiber_g: Optional[float] = Field(None, ge=0, description="Total fiber in grams.")
    sugars_g: Optional[float] = Field(None, ge=0, description="Total sugars in grams.")
    calories_kcal: Optional[float] = Field(None, ge=0, description="Total energy in kilocalories.")
    serving_weight_g: Optional[float] = Field(None, ge=0, description="Estimated total meal weight in grams.")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "carbs_g": 45.5,
            "protein_g": 12.0,
            "fat_g": 8.5,
            "fiber_g": 4.0,
            "sugars_g": 15.2,
            "calories_kcal": 320.0,
            "serving_weight_g": 350.0,
        }
    })


class MealTagsResponse(BaseModel):
    """Classification tags and carb-load class for the meal."""
    tags: list[str] = Field(
        default_factory=list,
        description="List of meal classification tags (e.g., low-carb, high-fat, moderate-carb).",
    )
    carb_load_class: str = Field(
        default="moderate",
        description="Carb load classification: light, moderate, or heavy.",
    )


class FoodProvenanceResponse(BaseModel):
    """Provenance and confidence information for a resolved food item."""
    source_name: str = Field(..., description="Data source name (openfoodfacts, user_foods, usda, etc.).")
    barcode_match: bool = Field(False, description="Whether the item was resolved via exact barcode match.")
    serving_certainty: float = Field(default=0.5, ge=0, le=1, description="Certainty of serving size estimation.")
    source_trust_tier: SourceTrustTier = Field(
        default=SourceTrustTier.ESTIMATED,
        description="Trust tier for the data source.",
    )
    quality_flags: list[str] = Field(
        default_factory=list,
        description="Any quality issues detected (e.g., missing_carbs, missing_serving_grams).",
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "source_name": "openfoodfacts",
            "barcode_match": True,
            "serving_certainty": 0.9,
            "source_trust_tier": "official",
            "quality_flags": [],
        }
    })


class PersonalContextSummary(BaseModel):
    """User's metabolic context at the time of the request."""
    current_glucose_mgdl: Optional[float] = Field(None, ge=20, le=600, description="Current glucose in mg/dL.")
    glucose_trend: Optional[str] = Field(None, description="Trend direction (rising, falling, flat).")
    hour_of_day: Optional[int] = Field(None, ge=0, le=23, description="Hour of day at meal time (0-23).")
    recent_history_hours: Optional[float] = Field(None, ge=0, description="Recent glucose history window in hours.")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "current_glucose_mgdl": 105,
            "glucose_trend": "flat",
            "hour_of_day": 7,
            "recent_history_hours": 6.0,
        }
    })


class ForecastWindowSchema(BaseModel):
    """A time window for forecast effects."""
    earliest_minutes: int = Field(..., ge=0, description="Start of window in minutes after eating.")
    latest_minutes: int = Field(..., ge=0, description="End of window in minutes after eating.")

    model_config = ConfigDict(json_schema_extra={
        "example": {"earliest_minutes": 15, "latest_minutes": 45}
    })


class ForecastEvidenceSchema(BaseModel):
    """A single piece of evidence supporting a forecast conclusion."""
    key: str = Field(..., description="Evidence identifier (e.g., carb_load, high_fat, elevated_baseline).")
    value: str = Field(..., description="Human-readable evidence description.")
    weight: float = Field(default=1.0, ge=0, le=2, description="Impact weight on confidence.")

    model_config = ConfigDict(json_schema_extra={
        "example": [
            {"key": "carb_load", "value": "Moderate carbs (45g)", "weight": 1.0},
            {"key": "high_fat", "value": "High fat content: 22g", "weight": 1.2},
        ]
    })


class ForecastDetail(BaseModel):
    """Detailed meal forecast output."""
    risk_level: RiskLevel = Field(..., description="Predicted glucose impact risk.")
    confidence: float = Field(..., ge=0, le=1, description="Overall forecast confidence (0.0 to 1.0).")
    confidence_tier: ConfidenceTier = Field(..., description="Human-readable confidence tier.")
    delayed_effect: bool = Field(False, description="Whether a delayed glucose response is expected (e.g., high-fat meal).")
    timing_onset_window: ForecastWindowSchema = Field(
        ..., description="Expected window for initial glucose change after eating."
    )
    peak_window: ForecastWindowSchema = Field(
        ..., description="Expected window for peak glucose effect."
    )
    evidence: list[ForecastEvidenceSchema] = Field(
        default_factory=list,
        description="List of evidence items supporting this forecast.",
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "risk_level": "moderate",
            "confidence": 0.72,
            "confidence_tier": "moderate",
            "delayed_effect": False,
            "timing_onset_window": {"earliest_minutes": 15, "latest_minutes": 45},
            "peak_window": {"earliest_minutes": 60, "latest_minutes": 120},
            "evidence": [
                {"key": "carb_load", "value": "Moderate carbs (45g)", "weight": 1.0},
            ],
        }
    })


class SafetyInfo(BaseModel):
    """Safety validation information for the forecast."""
    is_safe: bool = Field(True, description="Whether the forecast passed all safety checks.")
    disclaimer: str = Field(
        default=(
            "This forecast is for educational purposes only and does not constitute "
            "medical advice. Individual responses may vary. Always consult your "
            "healthcare provider before making changes to your diabetes management."
        ),
        description="Required medical disclaimer.",
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "is_safe": True,
            "disclaimer": "This forecast is for educational purposes only..."
        }
    })


class MealForecastResponse(BaseModel):
    """Complete meal forecast response.

    The canonical output contract for the meal forecasting feature.
    Contains the forecast, evidence, safety info, and narrative.
    """

    # ── Version and identity ──
    version: str = Field(
        default="1.0.0",
        description="Schema version for forward/backward compatibility.",
    )
    request_timestamp: datetime = Field(
        ..., description="When this forecast was generated (server time)."
    )

    # ── Meal summary ──
    meal_items: list[MealItemSchema] = Field(
        ..., description="The meal items that were evaluated."
    )
    nutrient_totals: NutrientTotals = Field(
        ..., description="Aggregated nutrient totals for the meal."
    )
    meal_tags: MealTagsResponse = Field(
        ..., description="Classification tags for the meal."
    )

    # ── Food provenance ──
    provenance: list[FoodProvenanceResponse] = Field(
        default_factory=list,
        description="Provenance information per resolved food item.",
    )

    # ── Personal context ──
    personal_context: PersonalContextSummary = Field(
        ..., description="User's metabolic context used in forecasting."
    )

    # ── Forecast ──
    forecast: ForecastDetail = Field(
        ..., description="The detailed meal forecast."
    )

    # ── Safety ──
    safety: SafetyInfo = Field(
        ..., description="Safety validation information."
    )

    # ── Narrative ──
    narrative: str = Field(
        "", description="Deterministic educational narrative explaining the forecast."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "1.0.0",
                "request_timestamp": "2026-05-21T07:30:05.123Z",
                "meal_items": [
                    {"name": "oatmeal", "quantity": 1, "unit": "serving", "barcode": "5901234123457", "brand": None},
                    {"name": "banana", "quantity": 1, "unit": "medium", "barcode": "4012345678901", "brand": None},
                ],
                "nutrient_totals": {
                    "carbs_g": 45.5,
                    "protein_g": 12.0,
                    "fat_g": 8.5,
                    "fiber_g": 4.0,
                    "sugars_g": 15.2,
                    "calories_kcal": 320.0,
                    "serving_weight_g": 350.0,
                },
                "meal_tags": {
                    "tags": ["moderate-carb", "mixed-meal"],
                    "carb_load_class": "moderate",
                },
                "provenance": [
                    {
                        "source_name": "openfoodfacts",
                        "barcode_match": True,
                        "serving_certainty": 0.9,
                        "source_trust_tier": "official",
                        "quality_flags": [],
                    },
                    {
                        "source_name": "openfoodfacts",
                        "barcode_match": True,
                        "serving_certainty": 0.5,
                        "source_trust_tier": "community",
                        "quality_flags": ["missing_serving_grams"],
                    },
                ],
                "personal_context": {
                    "current_glucose_mgdl": 105,
                    "glucose_trend": "flat",
                    "hour_of_day": 7,
                    "recent_history_hours": 6.0,
                },
                "forecast": {
                    "risk_level": "moderate",
                    "confidence": 0.72,
                    "confidence_tier": "moderate",
                    "delayed_effect": False,
                    "timing_onset_window": {"earliest_minutes": 15, "latest_minutes": 45},
                    "peak_window": {"earliest_minutes": 60, "latest_minutes": 120},
                    "evidence": [
                        {"key": "carb_load", "value": "Moderate carbs (45g)", "weight": 1.0},
                    ],
                },
                "safety": {
                    "is_safe": True,
                    "disclaimer": "This forecast is for educational purposes only...",
                },
                "narrative": "This meal has a moderate carbohydrate load. Glucose changes typically begin 15-45 minutes after eating, peaking around 60-120 minutes. The forecast has moderate confidence. This is educational context from your data patterns, not medical advice.",
            }
        },
    )


# ──────────────────────────────────────────────
# Serialization helpers
# ──────────────────────────────────────────────


def confidence_to_tier(confidence: float) -> ConfidenceTier:
    """Map a numeric confidence score to a ConfidenceTier."""
    if confidence >= 0.8:
        return ConfidenceTier.HIGH
    elif confidence >= 0.6:
        return ConfidenceTier.MODERATE
    else:
        return ConfidenceTier.LOW


def risk_level_to_tier(risk: RiskLevel) -> int:
    """Map RiskLevel enum to an integer score for ordering."""
    return {
        RiskLevel.LOW: 1,
        RiskLevel.MODERATE: 2,
        RiskLevel.HIGH: 3,
        RiskLevel.VERY_HIGH: 4,
    }.get(risk, 0)