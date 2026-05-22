"""Tests for forecast safety validator."""

import pytest

from app.services.forecast_safety_validator import (
    validate_forecast_text,
    sanitize_forecast_narrative,
    validate_forecast_output,
    ensure_safe_response,
    ForecastValidationError,
    FORBIDDEN_KEYWORDS,
)
from app.services.meal_forecast_engine import (
    MealForecast,
    RiskLevel,
    ForecastEvidence,
    ForecastWindow,
)


class TestValidateForecastText:
    """Tests for text validation."""

    def test_clean_text_passes(self):
        """Clean educational text should pass validation."""
        text = "This meal has moderate carbohydrate content and may cause a glucose rise."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is True
        assert violations == []

    def test_bolus_detection(self):
        """Bolus suggestions should be detected."""
        text = "You should take a bolus of 4 units for this meal."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is False
        assert len(violations) > 0

    def test_correction_factor_detection(self):
        """Correction factor suggestions should be detected."""
        text = "Apply a correction factor of 1800 for your current glucose."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is False

    def test_insulin_to_carb_ratio_detection(self):
        """Insulin-to-carb ratio suggestions should be detected."""
        text = "Using a 10:1 insulin-to-carb ratio, you need 6 units."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is False

    def test_safe_meal_insulin_phrase(self):
        """The phrase 'meal insulin' should be safe."""
        text = "This requires meal insulin consideration."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is True

    def test_keyword_detection(self):
        """Forbidden keywords in dangerous contexts should be detected."""
        text = "This bolus calculation is not appropriate here."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is False


class TestSanitizeForecastNarrative:
    """Tests for narrative sanitization."""

    def test_sanitize_removes_dosing(self):
        """Sanitization should remove dosing suggestions."""
        narrative = "You should take a correction bolus of 2 units."
        sanitized = sanitize_forecast_narrative(narrative)
        assert "correction" not in sanitized.lower()
        assert "bolus" not in sanitized.lower()
        assert "[REMOVED" in sanitized

    def test_sanitize_preserves_educational_content(self):
        """Sanitization should preserve non-dangerous educational content."""
        narrative = "This meal has 45g carbs which is moderate."
        sanitized = sanitize_forecast_narrative(narrative)
        assert "moderate" in sanitized

    def test_sanitize_clean_text_unchanged(self):
        """Clean text should pass through unchanged."""
        narrative = "This meal has moderate carbohydrate content."
        sanitized = sanitize_forecast_narrative(narrative)
        assert sanitized == narrative


class TestValidateForecastOutput:
    """Tests for full forecast validation."""

    def test_valid_forecast_passes(self):
        """A valid forecast should pass validation."""
        forecast = MealForecast(
            risk_level=RiskLevel.MODERATE,
            timing_onset_window=ForecastWindow(earliest_minutes=30, latest_minutes=60),
            peak_window=ForecastWindow(earliest_minutes=90, latest_minutes=120),
            delayed_effect=False,
            confidence=0.7,
            evidence=[ForecastEvidence(key="test", value="moderate carbs")],
        )
        is_valid, violations = validate_forecast_output(forecast, "Safe text")
        assert is_valid is True

    def test_forecast_with_violations_fails(self):
        """Forecast with dangerous narrative should fail."""
        forecast = MealForecast(
            risk_level=RiskLevel.HIGH,
            timing_onset_window=ForecastWindow(earliest_minutes=15, latest_minutes=45),
            peak_window=ForecastWindow(earliest_minutes=60, latest_minutes=120),
            delayed_effect=False,
            confidence=0.8,
            evidence=[],
        )
        is_valid, violations = validate_forecast_output(
            forecast, "You should take a bolus of 3 units"
        )
        assert is_valid is False
        assert len(violations) > 0


class TestEnsureSafeResponse:
    """Tests for safe response generation."""

    def test_safe_response_returns_valid_narrative(self):
        """Should return safe narrative for clean input."""
        forecast = MealForecast(
            risk_level=RiskLevel.MODERATE,
            timing_onset_window=ForecastWindow(earliest_minutes=30, latest_minutes=60),
            peak_window=ForecastWindow(earliest_minutes=90, latest_minutes=120),
            delayed_effect=False,
            confidence=0.7,
            evidence=[],
        )
        narrative = "This meal has moderate carbs."
        safe = ensure_safe_response(narrative, forecast)
        assert safe == narrative

    def test_dangerous_response_returns_disclaimer(self):
        """Should return safe disclaimer for dangerous input."""
        forecast = MealForecast(
            risk_level=RiskLevel.HIGH,
            timing_onset_window=ForecastWindow(earliest_minutes=15, latest_minutes=45),
            peak_window=ForecastWindow(earliest_minutes=60, latest_minutes=120),
            delayed_effect=False,
            confidence=0.8,
            evidence=[],
        )
        narrative = "You should take a correction bolus of 5 units."
        safe = ensure_safe_response(narrative, forecast)
        assert "disclaim" in safe.lower() or "consult" in safe.lower()