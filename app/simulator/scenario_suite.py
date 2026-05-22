"""Simulator scenario suite for meal forecast validation.

This module runs meal forecast scenarios against simulated patient data
to verify forecast timing, risk level, and confidence behavior.

Scenarios are designed to test specific forecast behaviors:
- high_carb_breakfast — heavy carb load, rapid rise expected
- low_carb_breakfast — minimal impact, low risk
- mixed_lunch — moderate rise, standard timing
- high_fat_dinner — delayed onset due to fat
- snack_before_exercise — light impact, pre-exercise context
- low_baseline_meal — meal when glucose is low
- high_baseline_meal — meal when glucose is high
"""

from dataclasses import dataclass
from typing import Any

from app.food.nutrient_extractor import NutrientProfile
from app.food.meal_composition import MealItem
from app.services.personal_context_service import PersonalContext, TrendClass
from app.services.baseline_features import HourBaselineFeatures
from app.services.meal_forecast_engine import RiskLevel, MealForecast
from app.services.meal_forecast_service import (
    MealForecastRequest,
    MealForecastResponse,
    generate_meal_forecast,
)


@dataclass
class ForecastScenario:
    """A meal forecast scenario for testing against simulated users."""
    name: str
    description: str
    # Nutrient profile for the meal (actual grams, not per 100g)
    carbs_g: float
    protein_g: float
    fat_g: float
    calories_kcal: float
    # Expected forecast characteristics
    expected_risk_range: tuple[RiskLevel, ...]
    expected_timing_range: tuple[int, int]  # onet window (min, max) in minutes
    expected_delayed: bool = False  # whether delayed effect is expected


# Scenario definitions aligned with the task requirements
SCENARIOS: list[ForecastScenario] = [
    ForecastScenario(
        name="high_carb_breakfast",
        description="High-carb breakfast like cereal or toast (45-60g carbs)",
        carbs_g=50, protein_g=8, fat_g=5, calories_kcal=280,
        expected_risk_range=(RiskLevel.HIGH, RiskLevel.VERY_HIGH),
        expected_timing_range=(15, 45),
    ),
    ForecastScenario(
        name="low_carb_breakfast",
        description="Low-carb breakfast like eggs and bacon (5-10g carbs)",
        carbs_g=8, protein_g=15, fat_g=12, calories_kcal=200,
        expected_risk_range=(RiskLevel.LOW,),
        expected_timing_range=(15, 30),
    ),
    ForecastScenario(
        name="mixed_lunch",
        description="Mixed lunch with carbs, protein, and moderate fat (40-50g carbs)",
        carbs_g=45, protein_g=20, fat_g=15, calories_kcal=400,
        expected_risk_range=(RiskLevel.MODERATE, RiskLevel.HIGH),
        expected_timing_range=(15, 60),
    ),
    ForecastScenario(
        name="high_fat_dinner",
        description="High-fat dinner with delayed effect (30g carbs, 35g fat)",
        carbs_g=30, protein_g=15, fat_g=35, calories_kcal=550,
        expected_risk_range=(RiskLevel.MODERATE, RiskLevel.HIGH),
        expected_timing_range=(20, 90),  # delayed due to fat
        expected_delayed=True,
    ),
    ForecastScenario(
        name="snack_before_exercise",
        description="Light snack before exercise (15g carbs)",
        carbs_g=15, protein_g=2, fat_g=0, calories_kcal=60,
        expected_risk_range=(RiskLevel.LOW,),
        expected_timing_range=(10, 30),
    ),
    ForecastScenario(
        name="low_baseline_meal",
        description="Meal when starting low (70 mg/dL glucose)",
        carbs_g=25, protein_g=5, fat_g=3, calories_kcal=120,
        expected_risk_range=(RiskLevel.MODERATE,),
        expected_timing_range=(15, 45),
    ),
    ForecastScenario(
        name="high_baseline_meal",
        description="Meal when starting high (180 mg/dL glucose)",
        carbs_g=25, protein_g=5, fat_g=3, calories_kcal=120,
        expected_risk_range=(RiskLevel.HIGH, RiskLevel.VERY_HIGH),
        expected_timing_range=(20, 60),
    ),
]


def create_test_meal_items(scenario: ForecastScenario) -> list[MealItem]:
    """Create mock MealItem objects from a scenario definition.
    
    Returns a single composite meal item with the scenario's nutrient totals.
    For testing, we create a mock food where the per-100g values equal the
    scenario totals, then use quantity=1.0 to get exactly those values.
    """
    from app.food.models import OpenFoodFactsProduct
    
    # Create a mock OpenFoodFactsProduct with per-100g values matching scenario
    # Use quantity=100g to get the full per-100g values
    mock_food = OpenFoodFactsProduct(
        code=f"scenario_{scenario.name}",
        product_name=scenario.name,
        carbs_100g=scenario.carbs_g,
        fiber_100g=2.0,  # typical
        sugars_100g=scenario.carbs_g * 0.5,  # assume 50% of carbs are sugars
        proteins_100g=scenario.protein_g,
        fat_100g=scenario.fat_g,
        energy_kcal_100g=scenario.calories_kcal,
        serving_quantity=100.0,
    )
    
    # Use 100g quantity to get the full per-100g values
    return [MealItem(food=mock_food, quantity=100.0, unit="g")]


def run_scenario(
    scenario: ForecastScenario,
    current_glucose: float = 100,
    hour_of_day: int = 12,
    glucose_trend: TrendClass = TrendClass.FLAT,
) -> dict[str, Any]:
    """Run a meal forecast scenario and return evaluation results.
    
    Args:
        scenario: The scenario to run
        current_glucose: Starting glucose level (mg/dL)
        hour_of_day: Hour for personal context (0-23)
        glucose_trend: Current glucose trend direction
        
    Returns:
        Dict with scenario name, expected/actual values, and pass/fail status
    """
    # Create meal items from scenario
    items = create_test_meal_items(scenario)
    
    # Create request
    request = MealForecastRequest(
        items=items,
        user_id=999999,  # test user id
    )
    
    # Create personal context
    context = PersonalContext(
        current_glucose=current_glucose,
        glucose_trend=glucose_trend,
        glucose_trend_rate=0.0,
        hour_of_day=hour_of_day,
        recent_glucose_history=[current_glucose] * 6,
        recent_history_hours=6,
        confidence=0.8,
    )
    
    # Generate forecast
    response = generate_meal_forecast(request, context)
    
    # Extract results
    forecast = response.forecast
    expected_risk_min = min(scenario.expected_risk_range)
    expected_risk_max = max(scenario.expected_risk_range)
    
    # Check risk level
    risk_passed = forecast.risk_level in scenario.expected_risk_range
    
    # Check timing (onset window)
    actual_timing = (
        forecast.timing_onset_window.earliest_minutes,
        forecast.timing_onset_window.latest_minutes,
    )
    timing_passed = (
        scenario.expected_timing_range[0] <= actual_timing[0] <= scenario.expected_timing_range[1]
        and scenario.expected_timing_range[0] <= actual_timing[1] <= scenario.expected_timing_range[1]
    )
    
    # Check delayed effect if expected
    delayed_passed = forecast.delayed_effect == scenario.expected_delayed
    
    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "expected_risk": [r.value for r in scenario.expected_risk_range],
        "actual_risk": forecast.risk_level.value,
        "expected_timing_min_max": scenario.expected_timing_range,
        "actual_timing_min_max": actual_timing,
        "expected_delayed": scenario.expected_delayed,
        "actual_delayed": forecast.delayed_effect,
        "confidence": round(forecast.confidence, 3),
        "risk_passed": risk_passed,
        "timing_passed": timing_passed,
        "delayed_passed": delayed_passed,
        "passed": risk_passed and timing_passed and delayed_passed,
        "evidence": [e.key for e in forecast.evidence],
    }


def run_all_scenarios(
    current_glucose: float = 100,
    hour_of_day: int = 12,
    glucose_trend: TrendClass = TrendClass.FLAT,
) -> list[dict[str, Any]]:
    """Run all scenarios and return results.
    
    Args:
        current_glucose: Starting glucose for all scenarios
        hour_of_day: Hour for all scenarios
        glucose_trend: Trend for all scenarios
        
    Returns:
        List of result dicts for each scenario
    """
    return [run_scenario(s, current_glucose, hour_of_day, glucose_trend) for s in SCENARIOS]


def run_scenarios_for_baseline_scenarios() -> list[dict[str, Any]]:
    """Run scenarios with different baseline glucose levels.
    
    Returns:
        Results for low and high baseline scenarios specially configured.
    """
    results = []
    
    # Low baseline (70 mg/dL)
    low_baseline_scenarios = [
        s for s in SCENARIOS 
        if s.name in {"low_baseline_meal", "low_carb_breakfast"}
    ]
    for scenario in low_baseline_scenarios:
        results.append(run_scenario(
            scenario,
            current_glucose=70,
            hour_of_day=8,  # morning
            glucose_trend=TrendClass.FALLING,
        ))
    
    # High baseline (180 mg/dL)
    high_baseline_scenarios = [
        s for s in SCENARIOS 
        if s.name in {"high_baseline_meal", "high_carb_breakfast"}
    ]
    for scenario in high_baseline_scenarios:
        results.append(run_scenario(
            scenario,
            current_glucose=180,
            hour_of_day=13,  # afternoon
            glucose_trend=TrendClass.RISING,
        ))
    
    return results