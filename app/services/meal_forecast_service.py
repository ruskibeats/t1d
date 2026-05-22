"""Meal forecast service - unified service for meal forecasting.

Wires together food normalization, meal composition, personal context,
forecast engine, safety validator, and narrative generator.
"""

from typing import Optional, List
from dataclasses import dataclass

from app.food.nutrient_extractor import NutrientProfile
from app.food.meal_composition import MealComposition, MealItem
from app.food.meal_tags import generate_meal_tags, MealTags
from app.services.personal_context_service import PersonalContext
from app.services.baseline_features import HourBaselineFeatures
from app.services.meal_forecast_engine import MealForecast, compute_meal_forecast
from app.services.safety_validator import enforce_safety
from app.services.narrative_generator import generate_narrative


@dataclass
class MealForecastRequest:
    """Request input for meal forecast."""
    items: List[MealItem]
    user_id: int


@dataclass
class MealForecastResponse:
    """Response from meal forecast."""
    forecast: MealForecast
    narrative: str
    confidence: float


def generate_meal_forecast(
    request: MealForecastRequest,
    personal_context: PersonalContext,
    hour_baseline: Optional[HourBaselineFeatures] = None,
) -> MealForecastResponse:
    """Generate complete meal forecast response.
    
    Args:
        request: Meal forecast request with food items
        personal_context: User's current context
        hour_baseline: Optional hour-of-day baseline
        
    Returns:
        MealForecastResponse with forecast and narrative
    """
    # Compose meal
    composition = compose_meal_from_items(request.items)
    
    # Generate tags
    tags = generate_meal_tags(composition.total_nutrients)
    
    # Compute forecast
    forecast = compute_meal_forecast(
        nutrients=composition.total_nutrients,
        meal_tags=tags.tags,
        provenance=composition.provenance,
        personal_context=personal_context,
        hour_baseline=hour_baseline,
    )
    
    # Generate narrative
    narrative = generate_narrative(forecast)
    
    # Enforce safety
    safe_forecast, safe_narrative, violations = enforce_safety(forecast, narrative)
    
    return MealForecastResponse(
        forecast=safe_forecast,
        narrative=safe_narrative or narrative,
        confidence=safe_forecast.confidence,
    )


def compose_meal_from_items(items: List[MealItem]) -> MealComposition:
    """Compose meal from item list."""
    from app.food.meal_composition import compose_meal
    return compose_meal(items)