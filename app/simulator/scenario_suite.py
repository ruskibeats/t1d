"""Simulator scenario suite for meal forecast validation.

This module runs meal forecast scenarios against repeatable synthetic contexts
to verify forecast timing, risk level, and confidence behavior.

Each scenario defines:
- Meal composition (nutrients)
- Personal context (glucose, trend, hour)
- Expected forecast characteristics (risk range, timing, delayed flag)

The suite can be run in CI or locally to detect regressions in forecast behavior.

Scenarios are deterministic: same inputs always produce same outputs.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.food.nutrient_extractor import NutrientProfile
from app.food.meal_composition import MealItem
from app.food.provenance import FoodProvenance, SourceTrustTier
from app.services.personal_context_service import PersonalContext, TrendClass
from app.services.meal_forecast_engine import RiskLevel, MealForecast
from app.services.meal_forecast_service import (
    MealForecastRequest,
    MealForecastResponse,
    generate_meal_forecast,
)


# ──────────────────────────────────────────────
# Scenario context
# ──────────────────────────────────────────────

@dataclass
class ScenarioContext:
    """Personal context for a scenario run."""
    current_glucose: float = 100.0
    hour_of_day: int = 12
    glucose_trend: TrendClass = TrendClass.FLAT
    glucose_trend_rate: float = 0.0
    recent_history_hours: float = 6.0


# ──────────────────────────────────────────────
# Scenario definitions
# ──────────────────────────────────────────────

@dataclass
class ForecastScenario:
    """A meal forecast scenario for testing against synthetic contexts."""
    name: str
    description: str
    # Nutrient profile for the meal (actual grams, not per 100g)
    carbs_g: float
    protein_g: float
    fat_g: float
    calories_kcal: float
    # Expected forecast characteristics
    expected_risk_range: tuple[RiskLevel, ...]
    expected_timing_earliest: int  # onset earliest_minutes
    expected_timing_latest: int    # onset latest_minutes
    expected_delayed: bool = False
    # Personal context override (uses defaults if not set)
    context: Optional[ScenarioContext] = None


# ──────────────────────────────────────────────
# Scenario catalog
# ──────────────────────────────────────────────

SCENARIOS: list[ForecastScenario] = [
    ForecastScenario(
        name="high_carb_breakfast",
        description="High-carb breakfast: cereal/toast (55g carbs, morning, rising)",
        carbs_g=55, protein_g=8, fat_g=5, calories_kcal=290,
        expected_risk_range=(RiskLevel.HIGH, RiskLevel.VERY_HIGH),
        expected_timing_earliest=20,
        expected_timing_latest=60,
        context=ScenarioContext(
            current_glucose=110, hour_of_day=8,
            glucose_trend=TrendClass.RISING,
        ),
    ),
    ForecastScenario(
        name="low_carb_breakfast",
        description="Low-carb breakfast: eggs/bacon (8g carbs)",
        carbs_g=8, protein_g=15, fat_g=12, calories_kcal=200,
        expected_risk_range=(RiskLevel.LOW,),
        expected_timing_earliest=10,
        expected_timing_latest=30,
    ),
    ForecastScenario(
        name="mixed_lunch",
        description="Mixed lunch: sandwich/salad (45g carbs, moderate fat)",
        carbs_g=45, protein_g=20, fat_g=15, calories_kcal=400,
        expected_risk_range=(RiskLevel.MODERATE, RiskLevel.HIGH),
        expected_timing_earliest=15,
        expected_timing_latest=60,
    ),
    ForecastScenario(
        name="high_fat_dinner",
        description="High-fat dinner: pizza/steak (30g carbs, 35g fat, delayed)",
        carbs_g=30, protein_g=15, fat_g=35, calories_kcal=550,
        expected_risk_range=(RiskLevel.MODERATE, RiskLevel.HIGH),
        expected_timing_earliest=20,
        expected_timing_latest=60,
        expected_delayed=True,
    ),
    ForecastScenario(
        name="snack_before_exercise",
        description="Light snack: banana (14g carbs, pre-exercise)",
        carbs_g=14, protein_g=1, fat_g=0, calories_kcal=55,
        expected_risk_range=(RiskLevel.LOW,),
        expected_timing_earliest=10,
        expected_timing_latest=30,
    ),
    ForecastScenario(
        name="low_baseline_meal",
        description="Meal when low: 25g carbs at 70 mg/dL, falling trend",
        carbs_g=25, protein_g=5, fat_g=3, calories_kcal=120,
        expected_risk_range=(RiskLevel.MODERATE,),
        expected_timing_earliest=15,
        expected_timing_latest=45,
        context=ScenarioContext(
            current_glucose=70, hour_of_day=10,
            glucose_trend=TrendClass.FALLING,
        ),
    ),
    ForecastScenario(
        name="high_baseline_meal",
        description="Meal when high: 25g carbs at 180 mg/dL, rising trend",
        carbs_g=25, protein_g=5, fat_g=3, calories_kcal=120,
        expected_risk_range=(RiskLevel.HIGH, RiskLevel.VERY_HIGH),
        expected_timing_earliest=15,
        expected_timing_latest=45,
        context=ScenarioContext(
            current_glucose=180, hour_of_day=14,
            glucose_trend=TrendClass.RISING,
        ),
    ),
]


# ──────────────────────────────────────────────
# Scenario runner
# ──────────────────────────────────────────────

def _build_meal_items(scenario: ForecastScenario) -> list[MealItem]:
    """Build MealItem list from a scenario's nutrient totals.

    Creates a single composite food item using OpenFoodFactsProduct
    with per-100g values matching the scenario totals, using quantity=100g.
    """
    from app.food.models import OpenFoodFactsProduct

    mock_food = OpenFoodFactsProduct(
        code=f"scenario_{scenario.name}",
        product_name=scenario.name,
        carbs_100g=scenario.carbs_g,
        fiber_100g=2.0,
        sugars_100g=scenario.carbs_g * 0.5,
        proteins_100g=scenario.protein_g,
        fat_100g=scenario.fat_g,
        energy_kcal_100g=scenario.calories_kcal,
        serving_quantity=100.0,
    )
    return [MealItem(food=mock_food, quantity=100.0, unit="g")]


def _build_context(scenario: ForecastScenario) -> PersonalContext:
    """Build PersonalContext from scenario's context or defaults."""
    ctx = scenario.context or ScenarioContext()
    return PersonalContext(
        current_glucose=ctx.current_glucose,
        glucose_trend=ctx.glucose_trend,
        glucose_trend_rate=ctx.glucose_trend_rate,
        hour_of_day=ctx.hour_of_day,
        recent_glucose_history=[ctx.current_glucose] * 6,
        recent_history_hours=ctx.recent_history_hours,
        confidence=0.8,
    )


def run_scenario(scenario: ForecastScenario) -> dict[str, Any]:
    """Run a single meal forecast scenario and return evaluation results.

    Args:
        scenario: The scenario to run.

    Returns:
        Dict with scenario name, expected/actual values, and pass/fail status.
    """
    items = _build_meal_items(scenario)
    context = _build_context(scenario)

    request = MealForecastRequest(items=items, user_id=999999)
    response = generate_meal_forecast(request, context)
    forecast = response.forecast

    # Risk check
    risk_passed = forecast.risk_level in scenario.expected_risk_range

    # Timing check: actual onset window should overlap expected range
    actual_earliest = forecast.timing_onset_window.earliest_minutes
    actual_latest = forecast.timing_onset_window.latest_minutes
    timing_passed = (
        scenario.expected_timing_earliest <= actual_earliest <= scenario.expected_timing_latest
        and scenario.expected_timing_earliest <= actual_latest <= scenario.expected_timing_latest
    )

    # Delayed effect check
    delayed_passed = forecast.delayed_effect == scenario.expected_delayed

    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "expected_risk": [r.value for r in scenario.expected_risk_range],
        "actual_risk": forecast.risk_level.value,
        "expected_timing": (
            scenario.expected_timing_earliest,
            scenario.expected_timing_latest,
        ),
        "actual_timing": (actual_earliest, actual_latest),
        "expected_delayed": scenario.expected_delayed,
        "actual_delayed": forecast.delayed_effect,
        "confidence": round(forecast.confidence, 3),
        "risk_passed": risk_passed,
        "timing_passed": timing_passed,
        "delayed_passed": delayed_passed,
        "passed": risk_passed and timing_passed and delayed_passed,
        "evidence": [e.key for e in forecast.evidence],
    }


def run_all_scenarios() -> list[dict[str, Any]]:
    """Run all scenarios and return results."""
    return [run_scenario(s) for s in SCENARIOS]


# ──────────────────────────────────────────────
# Scenario evaluator (outcome comparison)
# ──────────────────────────────────────────────

@dataclass
class ScenarioEvaluation:
    """Full evaluation of a scenario run."""
    scenario_name: str
    passed: bool
    risk_passed: bool
    timing_passed: bool
    delayed_passed: bool
    actual_risk: str
    expected_risk: list[str]
    actual_timing: tuple[int, int]
    expected_timing: tuple[int, int]
    confidence: float
    evidence: list[str]


class ScenarioEvaluator:
    """Evaluates and persists scenario run results for regression tracking."""

    def __init__(self):
        self._results: list[ScenarioEvaluation] = []

    def evaluate_all(self) -> list[ScenarioEvaluation]:
        """Run all scenarios and return evaluations."""
        self._results = []
        for scenario in SCENARIOS:
            raw = run_scenario(scenario)
            evaluation = ScenarioEvaluation(
                scenario_name=raw["scenario"],
                passed=raw["passed"],
                risk_passed=raw["risk_passed"],
                timing_passed=raw["timing_passed"],
                delayed_passed=raw["delayed_passed"],
                actual_risk=raw["actual_risk"],
                expected_risk=raw["expected_risk"],
                actual_timing=raw["actual_timing"],
                expected_timing=raw["expected_timing"],
                confidence=raw["confidence"],
                evidence=raw["evidence"],
            )
            self._results.append(evaluation)
        return self._results

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self._results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self._results if r.passed)

    @property
    def total_count(self) -> int:
        return len(self._results)

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of the evaluation."""
        return {
            "total": self.total_count,
            "passed": self.pass_count,
            "failed": self.total_count - self.pass_count,
            "all_passed": self.all_passed,
            "scenarios": [
                {
                    "name": r.scenario_name,
                    "passed": r.passed,
                    "risk": r.actual_risk,
                    "timing": list(r.actual_timing),
                    "confidence": r.confidence,
                }
                for r in self._results
            ],
        }

    def get_regression_baseline(self) -> dict[str, dict[str, Any]]:
        """Return a deterministic baseline for regression comparison.

        This captures the exact forecast outputs for each scenario so
        that future runs can be compared to detect behavioral changes.
        """
        return {
            r.scenario_name: {
                "risk": r.actual_risk,
                "timing": list(r.actual_timing),
                "confidence": r.confidence,
                "evidence": r.evidence,
            }
            for r in self._results
        }

    def compare_to_baseline(
        self, baseline: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Compare current results to a previous baseline.

        Returns a list of changes (empty if no regressions).
        """
        regressions = []
        for r in self._results:
            key = r.scenario_name
            if key not in baseline:
                regressions.append({
                    "scenario": key,
                    "change": "new_scenario",
                    "message": f"Scenario '{key}' not in baseline",
                })
                continue
            base = baseline[key]
            if r.actual_risk != base["risk"]:
                regressions.append({
                    "scenario": key,
                    "change": "risk_level",
                    "from": base["risk"],
                    "to": r.actual_risk,
                })
            if list(r.actual_timing) != base["timing"]:
                regressions.append({
                    "scenario": key,
                    "change": "timing",
                    "from": base["timing"],
                    "to": list(r.actual_timing),
                })
            if abs(r.confidence - base["confidence"]) > 0.001:
                regressions.append({
                    "scenario": key,
                    "change": "confidence",
                    "from": base["confidence"],
                    "to": r.confidence,
                })
        return regressions


# ──────────────────────────────────────────────
# Convenience functions
# ──────────────────────────────────────────────

def run_scenarios_for_baseline_scenarios() -> list[dict[str, Any]]:
    """Run scenarios with their per-scenario context overrides.

    This is the preferred entry point for running the full suite,
    as it respects each scenario's context (glucose, hour, trend).
    """
    return [run_scenario(s) for s in SCENARIOS]


def print_suite_summary() -> None:
    """Print a human-readable summary of scenario suite results."""
    evaluator = ScenarioEvaluator()
    evaluator.evaluate_all()
    summary = evaluator.summary()

    print(f"\n{'='*60}")
    print(f"Meal Forecast Scenario Suite — {summary['passed']}/{summary['total']} passed")
    print(f"{'='*60}")
    for s in summary["scenarios"]:
        status = "✅" if s["passed"] else "❌"
        print(f"  {status} {s['name']}: risk={s['risk']}, timing={s['timing']}, conf={s['confidence']}")
    print(f"{'='*60}\n")
