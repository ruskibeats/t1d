#!/usr/bin/env python3
"""Golden test suite for T1D Companion forecasts.

Fixed meal scenarios with expected outcomes for regression detection.
Tests both forecast accuracy and companion language patterns.
"""

from __future__ import annotations

import pytest
from demo.forecast_engine import ForecastStage, MealTotals


# ── Test Fixtures ──

@pytest.fixture
def well_controlled_stage() -> ForecastStage:
    """Standard profile for most tests."""
    return ForecastStage(
        anchor_type="well_controlled",
        basal_mg_dl=119,
        carb_ratio=13.9,
        insulin_sensitivity=29.5,
        fat_delay_hours=1.5,
        exercise_drop_factor=1.13,
    )


@pytest.fixture
def high_fat_stage() -> ForecastStage:
    """Profile sensitive to fat/protein delays."""
    return ForecastStage(
        anchor_type="high_fat_delayed",
        basal_mg_dl=119,
        carb_ratio=13.9,
        insulin_sensitivity=29.5,
        fat_delay_hours=4.1,
        exercise_drop_factor=1.13,
    )


# ── Golden Meal Scenarios ──

def test_pizza_high_fat_delayed(high_fat_stage: ForecastStage):
    """Pizza: high fat/protein should trigger delayed absorption (fat_triggers_delay=True)."""
    totals = MealTotals(
        carbs_g=60,
        sugars_g=20,  # ~1/3 fast carbs
        fat_g=25,
        protein_g=20,
    )
    result = high_fat_stage.forecast(totals, hour=19)
    
    # Fat triggers delay flag should be set
    assert result.meal_drivers.get("fat_triggers_delay") == True, "Expected fat delay flag"
    
    # Peak should be significant (from fast + slow carbs)
    assert result.peak_mg_dl > 150, f"Expected significant rise, got {result.peak_mg_dl}"
    
    # The 4.1h fat_delay means 12g goes to delayed compartment (releases at ~246 min)
    # Peak time (~90min) is dominated by slow carbs, not delayed - this is correct behavior


def test_cereal_fast_spike(well_controlled_stage: ForecastStage):
    """Cereal: high sugar content should cause early peak (< 1h)."""
    totals = MealTotals(
        carbs_g=45,
        sugars_g=35,  # Most carbs are sugars
        fat_g=2,
    )
    result = well_controlled_stage.forecast(totals, hour=19)
    
    # Peak should be early
    assert result.peak_time_minutes <= 70, f"Expected early peak, got {result.peak_time_minutes}min"
    
    # Should show extended tail (fat threshold ≥ 15)
    # But for cereal, extended tail should be false (low fat)
    assert not result.meal_drivers.get("fat_triggers_delay"), "Cereal should not trigger fat delay"


def test_large_meal_with_uncertainty(well_controlled_stage: ForecastStage):
    """Large meal should produce uncertainty band."""
    totals = MealTotals(carbs_g=100, sugars_g=30, fat_g=20)
    result = well_controlled_stage.forecast(totals, hour=19, carb_range_g=(80, 120))
    
    assert result.uncertainty_band is not None, "Expected uncertainty band for large meal"
    assert result.uncertainty_band.peak_range_mg_dl[1] > result.peak_mg_dl
    assert result.meal_drivers.get("estimated_peak_rise_mg_dl", 0) > 0


def test_exercise_sensitive_profile_delay():
    """Exercise-sensitive profile should show different heat modifier."""
    stage = ForecastStage(
        anchor_type="exercise_sensitive",
        basal_mg_dl=119,
        carb_ratio=13.9,
        insulin_sensitivity=29.5,
        fat_delay_hours=1.5,
        exercise_drop_factor=1.5,  # Higher = more exercise sensitive
    )
    totals = MealTotals(carbs_g=50, sugars_g=15, fat_g=5)
    result = stage.forecast(totals, hour=19)
    
    # Exercise heat modifier should reduce the rise
    assert result.exercise_heat_modifier < 1.0, f"Expected heat modifier < 1.0, got {result.exercise_heat_modifier}"


def test_evidence_fields_populated(well_controlled_stage: ForecastStage):
    """Evidence fields should populate correctly after annotation."""
    from demo.forecast_engine import populate_evidence_fields
    
    totals = MealTotals(carbs_g=60, sugars_g=15, fat_g=20)
    result = well_controlled_stage.forecast(totals, hour=19)
    
    # top_drivers is auto-populated during forecast
    assert len(result.top_drivers) > 0, "Expected auto-populated top_drivers"
    assert result.historical_similarity_score is None
    
    # After population
    result = populate_evidence_fields(
        result,
        evidence_items=[{"food": "pizza", "confidence": 0.8}],
        historical_similarity_score=0.75,
        missing_info=["portion_uncertainty"],
        calibration=well_controlled_stage.calibration,
    )
    
    assert result.historical_similarity_score == 0.75
    assert "portion_uncertainty" in result.missing_information_flags
    assert len(result.evidence_items) == 1


# ── Language Safety Tests ──

def test_forecast_never_prescribes(well_controlled_stage: ForecastStage):
    """Forecast output should never contain dosing language."""
    totals = MealTotals(carbs_g=60, sugars_g=15, fat_g=10)
    result = well_controlled_stage.forecast(totals, hour=19)
    
    # Render the forecast to text
    from demo.forecast_renderer import render_forecast
    text = render_forecast(result)
    
    banned_phrases = ["insulin", "bolus", "dose", "units", "deliver", "injection"]
    for phrase in banned_phrases:
        assert phrase.lower() not in text.lower(), f"Found banned phrase '{phrase}' in forecast"