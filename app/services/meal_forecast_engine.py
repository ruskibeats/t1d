"""Deterministic meal forecast engine.

Turns meal composition and personal context into structured forecast outputs.
Fully testable, non-LLM, evidence-first.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from app.food.nutrient_extractor import NutrientProfile
from app.food.provenance import FoodProvenance
from app.services.personal_context_service import PersonalContext, TrendClass
from app.services.baseline_features import HourBaselineFeatures, GlucoseStability


class RiskLevel(str, Enum):
    """Risk level for post-meal glucose response."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very-high"


@dataclass
class ForecastEvidence:
    """Evidence backing a forecast conclusion."""
    key: str
    value: str
    weight: float = 1.0  # Impact on confidence (0-1)


@dataclass
class ForecastWindow:
    """Time window for forecast effects."""
    earliest_minutes: int
    latest_minutes: int


@dataclass
class MealForecast:
    """Structured forecast output for a meal."""
    risk_level: RiskLevel
    timing_onset_window: ForecastWindow
    peak_window: ForecastWindow
    delayed_effect: bool
    confidence: float  # 0.0 to 1.0
    evidence: List[ForecastEvidence] = field(default_factory=list)
    
    def add_evidence(self, key: str, value: str, weight: float = 1.0):
        """Add evidence to the forecast."""
        self.evidence.append(ForecastEvidence(key=key, value=value, weight=weight))
    
    def is_reliable(self) -> bool:
        """Return True if forecast has sufficient confidence."""
        return self.confidence >= 0.6


def compute_meal_forecast(
    nutrients: NutrientProfile,
    meal_tags: List[str],
    provenance: FoodProvenance,
    personal_context: PersonalContext,
    hour_baseline: Optional[HourBaselineFeatures] = None,
) -> MealForecast:
    """Compute meal forecast from inputs.
    
    Args:
        nutrients: Total nutrients for the meal
        meal_tags: Classification tags from meal composition
        provenance: Food data provenance/confidence
        personal_context: User's current metabolic context
        hour_baseline: Hour-specific baseline features
        
    Returns:
        MealForecast with risk level, timing windows, and evidence
    """
    forecast = MealForecast(
        risk_level=RiskLevel.LOW,
        timing_onset_window=ForecastWindow(earliest_minutes=15, latest_minutes=45),
        peak_window=ForecastWindow(earliest_minutes=60, latest_minutes=120),
        delayed_effect=False,
        confidence=0.5,
        evidence=[],
    )
    
    # Validate inputs
    if nutrients.carbs_g is None:
        forecast.add_evidence("missing_carbs", "Cannot forecast without carb data", weight=0.0)
        forecast.confidence = 0.3
        return forecast
    
    carbs = nutrients.carbs_g
    fat_g = nutrients.fat_g or 0
    protein_g = nutrients.protein_g or 0
    
    # Calculate base confidence from provenance
    base_confidence = provenance.confidence_score()
    forecast.confidence = base_confidence
    
    # Carb load assessment
    if carbs < 15:
        carb_load = "light"
        forecast.add_evidence("carb_load", f"Light carbs ({carbs}g)")
    elif carbs < 45:
        carb_load = "moderate"
        forecast.add_evidence("carb_load", f"Moderate carbs ({carbs}g)")
    else:
        carb_load = "heavy"
        forecast.add_evidence("carb_load", f"Heavy carbs ({carbs}g)", weight=1.2)
    
    # Risk factors
    risk_score = 0.0
    
    # High carb load increases risk
    if carbs >= 45:
        risk_score += 2
        forecast.add_evidence("high_carb_risk", f"Heavy carb load: {carbs}g")
    elif carbs >= 20:
        risk_score += 1
    
    # Morning sensitivity
    if personal_context.hour_of_day in range(6, 11) and personal_context.glucose_trend == TrendClass.RISING:
        risk_score += 1
        forecast.add_evidence("morning_sensitivity", "Morning hours with rising trend")
    
    # Elevated baseline
    if personal_context.current_glucose and personal_context.current_glucose > 140:
        risk_score += 1
        forecast.add_evidence("elevated_baseline", f"Starting high: {personal_context.current_glucose}")
    
    # Mixed/high-fat meal
    if "high-fat" in meal_tags or fat_g >= 20:
        risk_score += 1
        forecast.add_evidence("high_fat", f"High fat content: {fat_g}g")
        # High fat can cause delayed effect
        forecast.delayed_effect = True
        forecast.peak_window = ForecastWindow(earliest_minutes=90, latest_minutes=180)
    
    # Poor provenance reduces confidence
    if not provenance.is_reliable():
        forecast.confidence *= 0.7
        forecast.add_evidence("sparse_history", "Limited food data quality")
    
    # Determine risk level
    if risk_score >= 3:
        forecast.risk_level = RiskLevel.VERY_HIGH
    elif risk_score == 2:
        forecast.risk_level = RiskLevel.HIGH
    elif risk_score == 1:
        forecast.risk_level = RiskLevel.MODERATE
    else:
        forecast.risk_level = RiskLevel.LOW
    
    # Adjust timing windows based on meal size and fat content
    if carbs > 50:
        forecast.timing_onset_window = ForecastWindow(earliest_minutes=20, latest_minutes=60)
        forecast.peak_window = ForecastWindow(earliest_minutes=90, latest_minutes=150)
    elif carbs < 15:
        # Light meals have earlier onset
        forecast.timing_onset_window = ForecastWindow(earliest_minutes=10, latest_minutes=30)
    
    # High fat meals have delayed onset
    if fat_g >= 20:
        forecast.delayed_effect = True
        forecast.timing_onset_window = ForecastWindow(earliest_minutes=20, latest_minutes=60)
        forecast.peak_window = ForecastWindow(earliest_minutes=90, latest_minutes=180)
    
    # Clamp confidence
    forecast.confidence = max(0.1, min(1.0, forecast.confidence))

    # ── Post-forecast safety validation ──
    # Lazy import to avoid circular dependency (forecast_safety_validator imports MealForecast)
    from app.services.forecast_safety_validator import validate_forecast_text

    safe_evidence: list[ForecastEvidence] = []
    for ev in forecast.evidence:
        is_safe, _violations = validate_forecast_text(ev.value)
        if is_safe:
            safe_evidence.append(ev)
        else:
            safe_evidence.append(
                ForecastEvidence(
                    key=ev.key,
                    value=f"{ev.key}: flagged for safety review (removed specific phrasing)",
                    weight=ev.weight * 0.5,
                )
            )
    forecast.evidence = safe_evidence

    return forecast


def forecast_from_meal_composition(
    meal_nutrients: NutrientProfile,
    meal_tags: List[str],
    provenance: FoodProvenance,
    personal_context: PersonalContext,
    hour_baseline: Optional[HourBaselineFeatures] = None,
) -> MealForecast:
    """Convenience wrapper for forecast computation."""
    return compute_meal_forecast(
        nutrients=meal_nutrients,
        meal_tags=meal_tags,
        provenance=provenance,
        personal_context=personal_context,
        hour_baseline=hour_baseline,
    )