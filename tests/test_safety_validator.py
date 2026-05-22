"""Tests for safety validator."""

import pytest

from app.services.safety_validator import (
    SafetyResult,
    validate_forecast_output,
    validate_text_output,
    enforce_safety,
    FORBIDDEN_PATTERNS,
    PROHIBITED_FIELDS,
)
from app.services.meal_forecast_engine import MealForecast, RiskLevel, ForecastWindow


class TestSafetyResult:
    """Tests for SafetyResult dataclass."""

    def test_safe_result(self):
        """Safe result has no violations."""
        result = SafetyResult(is_safe=True, violations=[])
        assert result.is_safe is True

    def test_unsafe_result(self):
        """Unsafe result has violations."""
        result = SafetyResult(is_safe=False, violations=["test violation"])
        assert result.is_safe is False


class TestValidateForecastOutput:
    """Tests for validate_forecast_output function."""

    def test_safe_forecast(self):
        """Clean forecast passes validation."""
        forecast = MealForecast(
            risk_level=RiskLevel.MODERATE,
            timing_onset_window=ForecastWindow(15, 45),
            peak_window=ForecastWindow(60, 120),
            delayed_effect=False,
            confidence=0.8,
        )
        
        result = validate_forecast_output(forecast)
        assert result.is_safe is True

    def test_forecast_with_prohibited_field(self):
        """Forecast with prohibited field fails."""
        forecast = MealForecast(
            risk_level=RiskLevel.MODERATE,
            timing_onset_window=ForecastWindow(15, 45),
            peak_window=ForecastWindow(60, 120),
            delayed_effect=False,
            confidence=0.8,
        )
        # Manually add a prohibited field to test detection
        forecast.insulin_units = 5
        
        result = validate_forecast_output(forecast)
        assert result.is_safe is False
        assert len(result.violations) > 0


class TestValidateTextOutput:
    """Tests for validate_text_output function."""

    def test_safe_text(self):
        """Safe text passes validation."""
        text = "This meal may cause a moderate glucose rise."
        result = validate_text_output(text)
        assert result.is_safe is True

    def test_dosing_advice_detected(self):
        """Text with dosing advice is flagged."""
        text = "Take 5 units of insulin with this meal."
        result = validate_text_output(text)
        assert result.is_safe is False
        assert "insulin" in result.violations[0].lower()

    def test_bolus_advice_detected(self):
        """Text with bolus advice is flagged."""
        text = "You should give yourself 3 units as a correction."
        result = validate_text_output(text)
        assert result.is_safe is False

    def test_correction_advice_detected(self):
        """Text with correction advice is flagged."""
        text = "Give a correction bolus of 2 units."
        result = validate_text_output(text)
        assert result.is_safe is False

    def test_sanitization(self):
        """Unsafe text is sanitized."""
        text = "Take 5 units of insulin with this meal."
        result = validate_text_output(text)
        
        assert result.sanitized_text != text
        assert "units" not in result.sanitized_text or "[REDACTED]" in result.sanitized_text


class TestForbiddenPatterns:
    """Tests for forbidden pattern detection."""

    def test_pattern_catches_insulin_units(self):
        """Pattern catches 'X units' phrasing."""
        text = "This requires 4 units of insulin."
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                assert True
                return
        assert False, "No pattern matched"

    def test_pattern_catches_bolus(self):
        """Pattern catches bolus advice."""
        text = "Take a bolus immediately."
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                assert True
                return
        assert False, "No pattern matched"

    def test_pattern_catches_correction(self):
        """Pattern catches correction advice."""
        text = "Give a correction dose of 2 units."
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                assert True
                return
        assert False, "No pattern matched"


class TestEnforceSafety:
    """Tests for enforce_safety function."""

    def test_enforces_text_safety(self):
        """Safety is enforced on text."""
        text = "Take 5 units with this meal."
        
        forecast = MealForecast(
            risk_level=RiskLevel.MODERATE,
            timing_onset_window=ForecastWindow(15, 45),
            peak_window=ForecastWindow(60, 120),
            delayed_effect=False,
            confidence=0.8,
        )
        
        _, safe_text, violations = enforce_safety(forecast, text)
        assert len(violations) > 0
        assert "[REDACTED]" in safe_text or safe_text != text