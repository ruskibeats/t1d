"""Tests for meal forecast engine."""

import pytest

from app.services.meal_forecast_engine import (
    MealForecast,
    RiskLevel,
    ForecastEvidence,
    ForecastWindow,
    compute_meal_forecast,
)
from app.food.nutrient_extractor import NutrientProfile
from app.food.provenance import FoodProvenance, SourceTrustTier
from app.services.personal_context_service import PersonalContext, TrendClass


class TestForecastEvidence:
    """Tests for ForecastEvidence dataclass."""

    def test_evidence_creation(self):
        """Evidence can be created."""
        ev = ForecastEvidence(key="test", value="some value", weight=0.8)
        assert ev.key == "test"
        assert ev.value == "some value"


class TestForecastWindow:
    """Tests for ForecastWindow dataclass."""

    def test_window_creation(self):
        """Window can be created."""
        window = ForecastWindow(earliest_minutes=30, latest_minutes=90)
        assert window.earliest_minutes == 30
        assert window.latest_minutes == 90


class TestMealForecast:
    """Tests for MealForecast dataclass."""

    def test_add_evidence(self):
        """Evidence can be added to forecast."""
        forecast = MealForecast(
            risk_level=RiskLevel.LOW,
            timing_onset_window=ForecastWindow(15, 45),
            peak_window=ForecastWindow(60, 120),
            delayed_effect=False,
            confidence=0.5,
        )
        forecast.add_evidence("test", "value")
        assert len(forecast.evidence) == 1

    def test_is_reliable_high_confidence(self):
        """Forecast is reliable with high confidence."""
        forecast = MealForecast(
            risk_level=RiskLevel.MODERATE,
            timing_onset_window=ForecastWindow(15, 45),
            peak_window=ForecastWindow(60, 120),
            delayed_effect=False,
            confidence=0.7,
        )
        assert forecast.is_reliable() is True

    def test_is_reliable_low_confidence(self):
        """Forecast is not reliable with low confidence."""
        forecast = MealForecast(
            risk_level=RiskLevel.LOW,
            timing_onset_window=ForecastWindow(15, 45),
            peak_window=ForecastWindow(60, 120),
            delayed_effect=False,
            confidence=0.4,
        )
        assert forecast.is_reliable() is False


class TestComputeMealForecast:
    """Tests for compute_meal_forecast function."""

    def test_light_carb_meal(self):
        """Light carb meal produces low risk forecast."""
        nutrients = NutrientProfile(carbs_g=10, protein_g=5, fat_g=3)
        provenance = FoodProvenance(
            source_name="test",
            source_trust_tier=SourceTrustTier.OFFICIAL,
            barcode_match=True,
        )
        context = PersonalContext(
            current_glucose=100,
            glucose_trend=TrendClass.FLAT,
            glucose_trend_rate=0,
            hour_of_day=12,
            recent_glucose_history=[100],
            recent_history_hours=24,
            confidence=0.9,
        )
        
        forecast = compute_meal_forecast(nutrients, [], provenance, context)
        
        assert forecast.risk_level == RiskLevel.LOW
        assert forecast.confidence >= 0.5

    def test_heavy_carb_meal(self):
        """Heavy carb meal produces higher risk forecast."""
        nutrients = NutrientProfile(carbs_g=60, protein_g=10, fat_g=5)
        provenance = FoodProvenance(
            source_name="test",
            source_trust_tier=SourceTrustTier.OFFICIAL,
            barcode_match=True,
        )
        context = PersonalContext(
            current_glucose=100,
            glucose_trend=TrendClass.FLAT,
            glucose_trend_rate=0,
            hour_of_day=12,
            recent_glucose_history=[100],
            recent_history_hours=24,
            confidence=0.9,
        )
        
        forecast = compute_meal_forecast(nutrients, [], provenance, context)
        
        assert forecast.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]

    def test_high_fat_meal(self):
        """High fat meal triggers delayed effect."""
        nutrients = NutrientProfile(carbs_g=30, protein_g=10, fat_g=30)
        provenance = FoodProvenance(
            source_name="test",
            source_trust_tier=SourceTrustTier.OFFICIAL,
            barcode_match=True,
        )
        context = PersonalContext(
            current_glucose=100,
            glucose_trend=TrendClass.FLAT,
            glucose_trend_rate=0,
            hour_of_day=12,
            recent_glucose_history=[100],
            recent_history_hours=24,
            confidence=0.9,
        )
        
        forecast = compute_meal_forecast(nutrients, [], provenance, context)
        
        assert forecast.delayed_effect is True
        assert forecast.peak_window.earliest_minutes >= 90

    def test_missing_carbs(self):
        """Missing carbs produces low confidence forecast."""
        nutrients = NutrientProfile(carbs_g=None)
        provenance = FoodProvenance(
            source_name="test",
            source_trust_tier=SourceTrustTier.OFFICIAL,
        )
        context = PersonalContext(
            current_glucose=100,
            glucose_trend=TrendClass.FLAT,
            glucose_trend_rate=0,
            hour_of_day=12,
            recent_glucose_history=[100],
            recent_history_hours=24,
            confidence=0.5,
        )
        
        forecast = compute_meal_forecast(nutrients, [], provenance, context)
        
        assert forecast.confidence < 0.5
        assert any(e.key == "missing_carbs" for e in forecast.evidence)


class TestDeterministicBehavior:
    """Tests for deterministic forecast behavior."""

    def test_same_input_same_output(self):
        """Identical inputs produce identical outputs."""
        nutrients = NutrientProfile(carbs_g=25, protein_g=10, fat_g=10)
        provenance = FoodProvenance(
            source_name="test",
            source_trust_tier=SourceTrustTier.OFFICIAL,
            barcode_match=True,
        )
        context = PersonalContext(
            current_glucose=120,
            glucose_trend=TrendClass.FLAT,
            glucose_trend_rate=0,
            hour_of_day=12,
            recent_glucose_history=[120, 118, 120],
            recent_history_hours=24,
            confidence=0.8,
        )
        
        forecast1 = compute_meal_forecast(nutrients, [], provenance, context)
        forecast2 = compute_meal_forecast(nutrients, [], provenance, context)
        
        assert forecast1.risk_level == forecast2.risk_level
        assert forecast1.confidence == forecast2.confidence
        assert len(forecast1.evidence) == len(forecast2.evidence)


class TestRealWorldScenarios:
    """Tests for real-world meal scenarios."""

    def test_eggs_bread_scenario(self):
        """Eggs + bread scenario from paste."""
        # Approximate: 2 eggs + 2 bread slices
        nutrients = NutrientProfile(
            carbs_g=30,
            protein_g=15,
            fat_g=15,  # Some fat from eggs
            calories_kcal=350,
        )
        provenance = FoodProvenance(
            source_name="test",
            source_trust_tier=SourceTrustTier.OFFICIAL,
            barcode_match=True,
        )
        context = PersonalContext(
            current_glucose=110,
            glucose_trend=TrendClass.FLAT,
            glucose_trend_rate=0,
            hour_of_day=12,
            recent_glucose_history=[110, 108, 110],
            recent_history_hours=24,
            confidence=0.8,
        )
        
        forecast = compute_meal_forecast(nutrients, [], provenance, context)
        
        assert forecast.risk_level in [RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.LOW]
        # Check that some evidence was added
        assert len(forecast.evidence) > 0