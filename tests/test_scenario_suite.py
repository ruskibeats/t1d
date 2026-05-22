"""Regression tests for the meal forecast scenario suite.

Verifies that:
1. All scenarios pass (risk, timing, delayed flag)
2. Results are deterministic across runs
3. Regression detection works (baseline comparison)
4. ScenarioEvaluator summary is correct
"""

import pytest

from app.simulator.scenario_suite import (
    SCENARIOS,
    ScenarioEvaluator,
    run_all_scenarios,
    run_scenario,
)
from app.services.meal_forecast_engine import RiskLevel


class TestScenarioSuite:
    """Tests for the scenario suite runner."""

    def test_all_scenarios_pass(self):
        """All 7 scenarios should pass with current engine."""
        results = run_all_scenarios()
        failed = [r for r in results if not r["passed"]]
        assert len(failed) == 0, (
            f"Failed scenarios: {[(f['scenario'], f) for f in failed]}"
        )

    def test_all_scenarios_deterministic(self):
        """Running the suite twice produces identical results."""
        run1 = run_all_scenarios()
        run2 = run_all_scenarios()
        assert len(run1) == len(run2)
        for r1, r2 in zip(run1, run2):
            assert r1["scenario"] == r2["scenario"]
            assert r1["actual_risk"] == r2["actual_risk"]
            assert r1["actual_timing"] == r2["actual_timing"]
            assert r1["confidence"] == r2["confidence"]
            assert r1["passed"] == r2["passed"]

    def test_seven_scenarios_defined(self):
        """The catalog should have exactly 7 scenarios."""
        assert len(SCENARIOS) == 7

    def test_scenario_names(self):
        """All expected scenario names should be present."""
        names = {s.name for s in SCENARIOS}
        expected = {
            "high_carb_breakfast",
            "low_carb_breakfast",
            "mixed_lunch",
            "high_fat_dinner",
            "snack_before_exercise",
            "low_baseline_meal",
            "high_baseline_meal",
        }
        assert names == expected

    def test_high_carb_breakfast_risk(self):
        """High-carb breakfast should produce HIGH or VERY_HIGH risk."""
        scenario = next(s for s in SCENARIOS if s.name == "high_carb_breakfast")
        result = run_scenario(scenario)
        assert result["actual_risk"] in ("high", "very-high")
        assert result["risk_passed"] is True

    def test_low_carb_breakfast_risk(self):
        """Low-carb breakfast should produce LOW risk."""
        scenario = next(s for s in SCENARIOS if s.name == "low_carb_breakfast")
        result = run_scenario(scenario)
        assert result["actual_risk"] == "low"
        assert result["risk_passed"] is True

    def test_high_fat_dinner_delayed(self):
        """High-fat dinner should trigger delayed_effect=True."""
        scenario = next(s for s in SCENARIOS if s.name == "high_fat_dinner")
        result = run_scenario(scenario)
        assert result["actual_delayed"] is True
        assert result["delayed_passed"] is True

    def test_high_baseline_elevated_risk(self):
        """Meal at 180 mg/dL with rising trend should be HIGH or VERY_HIGH."""
        scenario = next(s for s in SCENARIOS if s.name == "high_baseline_meal")
        result = run_scenario(scenario)
        assert result["actual_risk"] in ("high", "very-high")
        assert result["risk_passed"] is True

    def test_low_baseline_moderate_risk(self):
        """Meal at 70 mg/dL with falling trend should be MODERATE."""
        scenario = next(s for s in SCENARIOS if s.name == "low_baseline_meal")
        result = run_scenario(scenario)
        assert result["actual_risk"] == "moderate"
        assert result["risk_passed"] is True

    def test_snack_low_risk(self):
        """Light snack should produce LOW risk."""
        scenario = next(s for s in SCENARIOS if s.name == "snack_before_exercise")
        result = run_scenario(scenario)
        assert result["actual_risk"] == "low"
        assert result["risk_passed"] is True

    def test_mixed_lunch_moderate_or_high(self):
        """Mixed lunch should produce MODERATE or HIGH risk."""
        scenario = next(s for s in SCENARIOS if s.name == "mixed_lunch")
        result = run_scenario(scenario)
        assert result["actual_risk"] in ("moderate", "high")
        assert result["risk_passed"] is True


class TestScenarioEvaluator:
    """Tests for the ScenarioEvaluator class."""

    def test_evaluator_all_passed(self):
        """Evaluator should report all_passed=True when all scenarios pass."""
        evaluator = ScenarioEvaluator()
        evaluator.evaluate_all()
        assert evaluator.all_passed is True
        assert evaluator.pass_count == 7
        assert evaluator.total_count == 7

    def test_evaluator_summary(self):
        """Summary should have correct structure."""
        evaluator = ScenarioEvaluator()
        evaluator.evaluate_all()
        summary = evaluator.summary()
        assert summary["total"] == 7
        assert summary["passed"] == 7
        assert summary["failed"] == 0
        assert summary["all_passed"] is True
        assert len(summary["scenarios"]) == 7

    def test_regression_baseline_deterministic(self):
        """Regression baseline should be identical across runs."""
        e1 = ScenarioEvaluator()
        e1.evaluate_all()
        b1 = e1.get_regression_baseline()

        e2 = ScenarioEvaluator()
        e2.evaluate_all()
        b2 = e2.get_regression_baseline()

        assert b1 == b2

    def test_no_regressions_against_self(self):
        """Comparing results to own baseline should show no regressions."""
        evaluator = ScenarioEvaluator()
        evaluator.evaluate_all()
        baseline = evaluator.get_regression_baseline()
        regressions = evaluator.compare_to_baseline(baseline)
        assert regressions == []

    def test_regression_detection_risk_change(self):
        """Regression detection should catch risk level changes."""
        evaluator = ScenarioEvaluator()
        evaluator.evaluate_all()
        baseline = evaluator.get_regression_baseline()

        # Simulate a regression by modifying the baseline
        baseline["high_carb_breakfast"]["risk"] = "low"
        regressions = evaluator.compare_to_baseline(baseline)
        assert len(regressions) >= 1
        risk_changes = [r for r in regressions if r["change"] == "risk_level"]
        assert len(risk_changes) >= 1
        assert risk_changes[0]["scenario"] == "high_carb_breakfast"

    def test_regression_detection_timing_change(self):
        """Regression detection should catch timing changes."""
        evaluator = ScenarioEvaluator()
        evaluator.evaluate_all()
        baseline = evaluator.get_regression_baseline()

        baseline["low_carb_breakfast"]["timing"] = [99, 99]
        regressions = evaluator.compare_to_baseline(baseline)
        timing_changes = [r for r in regressions if r["change"] == "timing"]
        assert len(timing_changes) >= 1

    def test_regression_detection_new_scenario(self):
        """Regression detection should flag scenarios not in baseline."""
        evaluator = ScenarioEvaluator()
        evaluator.evaluate_all()
        # Empty baseline means all scenarios are "new"
        regressions = evaluator.compare_to_baseline({})
        assert len(regressions) == 7
        assert all(r["change"] == "new_scenario" for r in regressions)

    def test_baseline_has_all_scenarios(self):
        """Regression baseline should have entries for all 7 scenarios."""
        evaluator = ScenarioEvaluator()
        evaluator.evaluate_all()
        baseline = evaluator.get_regression_baseline()
        assert len(baseline) == 7
        for name in [
            "high_carb_breakfast", "low_carb_breakfast", "mixed_lunch",
            "high_fat_dinner", "snack_before_exercise",
            "low_baseline_meal", "high_baseline_meal",
        ]:
            assert name in baseline
            assert "risk" in baseline[name]
            assert "timing" in baseline[name]
            assert "confidence" in baseline[name]
            assert "evidence" in baseline[name]


class TestScenarioContextOverrides:
    """Tests that per-scenario context overrides work correctly."""

    def test_high_baseline_uses_180_glucose(self):
        """high_baseline_meal scenario should use 180 mg/dL glucose context."""
        scenario = next(s for s in SCENARIOS if s.name == "high_baseline_meal")
        assert scenario.context is not None
        assert scenario.context.current_glucose == 180

    def test_low_baseline_uses_70_glucose(self):
        """low_baseline_meal scenario should use 70 mg/dL glucose context."""
        scenario = next(s for s in SCENARIOS if s.name == "low_baseline_meal")
        assert scenario.context is not None
        assert scenario.context.current_glucose == 70

    def test_default_context_when_none(self):
        """Scenarios without context override should use defaults."""
        scenario = next(s for s in SCENARIOS if s.name == "mixed_lunch")
        assert scenario.context is None
        result = run_scenario(scenario)
        assert result["passed"] is True
