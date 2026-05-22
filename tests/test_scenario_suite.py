"""Tests for meal forecast scenario suite validation.

Runs the forecast scenarios against the meal forecast pipeline
to verify timing, risk level, and confidence behavior.
"""

import pytest

from app.services.meal_forecast_engine import RiskLevel
from app.services.personal_context_service import TrendClass
from app.simulator.scenario_suite import (
    SCENARIOS,
    ForecastScenario,
    run_scenario,
    run_all_scenarios,
    run_scenarios_for_baseline_scenarios,
)


class TestScenarioDefinitions:
    """Tests for scenario definitions."""

    def test_scenarios_exist(self):
        """All required scenarios are defined."""
        scenario_names = {s.name for s in SCENARIOS}
        required = {
            "high_carb_breakfast",
            "low_carb_breakfast",
            "mixed_lunch",
            "high_fat_dinner",
            "snack_before_exercise",
            "low_baseline_meal",
            "high_baseline_meal",
        }
        assert required == scenario_names

    def test_scenario_fields(self):
        """Each scenario has required fields."""
        for s in SCENARIOS:
            assert s.carbs_g > 0 or s.name == "snack_before_exercise"  # snacks can have low carbs
            assert s.protein_g >= 0
            assert s.fat_g >= 0
            assert s.calories_kcal > 0
            assert len(s.expected_risk_range) > 0
            assert s.expected_timing_range[0] >= 0
            assert s.expected_timing_range[1] > s.expected_timing_range[0]


class TestScenarioExecution:
    """Tests for scenario execution."""

    def test_high_carb_breakfast_risk(self):
        """High-carb breakfast produces high or very-high risk."""
        result = run_scenario(
            [s for s in SCENARIOS if s.name == "high_carb_breakfast"][0],
            current_glucose=100,
        )
        assert result["actual_risk"] in {"high", "very-high"}
        assert result["risk_passed"]

    def test_low_carb_breakfast_low_risk(self):
        """Low-carb breakfast produces low risk."""
        result = run_scenario(
            [s for s in SCENARIOS if s.name == "low_carb_breakfast"][0],
            current_glucose=100,
        )
        assert result["actual_risk"] == "low"
        assert result["risk_passed"]

    def test_high_fat_dinner_delayed(self):
        """High-fat dinner shows delayed effect."""
        result = run_scenario(
            [s for s in SCENARIOS if s.name == "high_fat_dinner"][0],
            current_glucose=100,
        )
        assert result["actual_delayed"] is True
        assert result["delayed_passed"]

    def test_snack_small_timing(self):
        """Snack has shorter timing window."""
        result = run_scenario(
            [s for s in SCENARIOS if s.name == "snack_before_exercise"][0],
            current_glucose=100,
            hour_of_day=15,  # afternoon
        )
        # Light snack should have shorter onset window
        assert result["actual_timing_min_max"][0] <= 30

    def test_all_scenarios_run_without_error(self):
        """All scenarios can be executed without error."""
        results = run_all_scenarios(current_glucose=100)
        assert len(results) == 7
        for r in results:
            assert "scenario" in r
            assert "passed" in r
            assert "actual_risk" in r
            assert "actual_timing_min_max" in r


class TestBaselineVariations:
    """Tests for different baseline glucose scenarios."""

    def test_low_baseline_scenario(self):
        """Low baseline scenario executes correctly."""
        results = run_scenarios_for_baseline_scenarios()
        low_results = [r for r in results if "low_baseline" in r["scenario"]]
        assert len(low_results) >= 1

    def test_high_baseline_scenario(self):
        """High baseline scenario executes correctly."""
        results = run_scenarios_for_baseline_scenarios()
        high_results = [r for r in results if "high_baseline" in r["scenario"]]
        assert len(high_results) >= 1


class TestDeterministicBehavior:
    """Tests for deterministic scenario behavior."""

    def test_same_input_same_output(self):
        """Same inputs produce identical outputs."""
        scenario = SCENARIOS[0]
        result1 = run_scenario(scenario, current_glucose=100, hour_of_day=12)
        result2 = run_scenario(scenario, current_glucose=100, hour_of_day=12)
        
        assert result1["actual_risk"] == result2["actual_risk"]
        assert result1["actual_timing_min_max"] == result2["actual_timing_min_max"]
        assert result1["confidence"] == result2["confidence"]

    def test_confidence_range(self):
        """Confidence is within valid range."""
        results = run_all_scenarios(current_glucose=100)
        for r in results:
            assert 0.0 <= r["confidence"] <= 1.0