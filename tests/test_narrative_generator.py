"""Tests for narrative generator."""

import pytest

from app.services.narrative_generator import (
    generate_narrative,
    rewrite_narrative_with_llm,
    _meal_summary_section,
    _risk_explanation_section,
    _timing_section,
    _confidence_section,
)
from app.services.meal_forecast_engine import MealForecast, RiskLevel, ForecastWindow


class TestGenerateNarrative:
    """Tests for generate_narrative function."""

    def test_low_risk_narrative(self):
        """Low risk generates appropriate narrative."""
        forecast = MealForecast(
            risk_level=RiskLevel.LOW,
            timing_onset_window=ForecastWindow(15, 30),
            peak_window=ForecastWindow(45, 75),
            delayed_effect=False,
            confidence=0.9,
        )
        
        narrative = generate_narrative(forecast)
        
        assert "light carbohydrate load" in narrative.lower()
        assert "educational context" in narrative.lower()

    def test_high_risk_narrative(self):
        """High risk generates appropriate narrative."""
        forecast = MealForecast(
            risk_level=RiskLevel.HIGH,
            timing_onset_window=ForecastWindow(20, 45),
            peak_window=ForecastWindow(60, 120),
            delayed_effect=False,
            confidence=0.8,
        )
        
        narrative = generate_narrative(forecast)
        
        assert "higher carbohydrate load" in narrative.lower()

    def test_delayed_effect_narrative(self):
        """Delayed effect is noted in narrative."""
        forecast = MealForecast(
            risk_level=RiskLevel.MODERATE,
            timing_onset_window=ForecastWindow(30, 60),
            peak_window=ForecastWindow(90, 150),
            delayed_effect=True,
            confidence=0.7,
        )
        
        narrative = generate_narrative(forecast)
        
        assert "delay" in narrative.lower()

    def test_no_dosing_advice(self):
        """Narrative contains no dosing advice."""
        forecast = MealForecast(
            risk_level=RiskLevel.VERY_HIGH,
            timing_onset_window=ForecastWindow(30, 60),
            peak_window=ForecastWindow(90, 150),
            delayed_effect=True,
            confidence=0.9,
        )
        
        narrative = generate_narrative(forecast)
        
        # Ensure no dosing language
        assert "units" not in narrative.lower() or "no units" in narrative.lower()
        assert "take" not in narrative.lower() or "not take" in narrative.lower()


class TestSectionFunctions:
    """Tests for individual section functions."""

    def test_meal_summary_low(self):
        """Low risk meal summary."""
        forecast = MealForecast(
            risk_level=RiskLevel.LOW,
            timing_onset_window=ForecastWindow(15, 30),
            peak_window=ForecastWindow(45, 75),
            delayed_effect=False,
            confidence=0.9,
        )
        section = _meal_summary_section(forecast)
        assert "light" in section.lower()

    def test_confidence_high(self):
        """High confidence section."""
        forecast = MealForecast(
            risk_level=RiskLevel.LOW,
            timing_onset_window=ForecastWindow(15, 30),
            peak_window=ForecastWindow(45, 75),
            delayed_effect=False,
            confidence=0.9,
        )
        section = _confidence_section(forecast)
        assert "high confidence" in section.lower()

    def test_confidence_low(self):
        """Low confidence section."""
        forecast = MealForecast(
            risk_level=RiskLevel.LOW,
            timing_onset_window=ForecastWindow(15, 30),
            peak_window=ForecastWindow(45, 75),
            delayed_effect=False,
            confidence=0.5,
        )
        section = _confidence_section(forecast)
        assert "limited confidence" in section.lower()


class TestRewriteNarrative:
    """Tests for rewrite_narrative_with_llm function."""

    def test_rewrite_disabled(self):
        """Rewrite returns original when flag is False."""
        narrative = "This is a test narrative."
        result = rewrite_narrative_with_llm(narrative, feature_flag=False)
        assert result == narrative

    def test_rewrite_enabled(self):
        """Rewrite returns original when flag is True (no LLM in test)."""
        narrative = "This is a test narrative."
        result = rewrite_narrative_with_llm(narrative, feature_flag=True)
        assert result == narrative