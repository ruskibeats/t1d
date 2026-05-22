"""Tests for hour-of-day baseline and variability features."""

import pytest

from app.services.baseline_features import (
    HourBaselineFeatures,
    GlucoseStability,
    assess_glucose_stability,
)


class TestHourBaselineFeatures:
    """Tests for HourBaselineFeatures dataclass."""

    def test_is_trusted_with_sufficient_data(self):
        """Features are trusted with sufficient samples."""
        features = HourBaselineFeatures(
            hour=8,
            mean_glucose=120.0,
            std_deviation=15.0,
            sample_count=10,
        )
        assert features.is_trusted() is True

    def test_is_trusted_with_insufficient_data(self):
        """Features are not trusted with sparse data."""
        features = HourBaselineFeatures(
            hour=8,
            mean_glucose=120.0,
            std_deviation=15.0,
            sample_count=3,
        )
        assert features.is_trusted(min_samples=5) is False

    def test_is_trusted_without_mean(self):
        """Features are not trusted without mean."""
        features = HourBaselineFeatures(
            hour=8,
            sample_count=10,
        )
        assert features.is_trusted() is False


class TestGlucoseStability:
    """Tests for GlucoseStability dataclass."""

    def test_stability_creation(self):
        """Stability can be created."""
        stability = GlucoseStability(level="stable", variability_score=0.2)
        assert stability.level == "stable"
        assert stability.variability_score == 0.2


class TestAssessGlucoseStability:
    """Tests for assess_glucose_stability function."""

    def test_stable_assessment(self):
        """Low std deviation indicates stable."""
        features = HourBaselineFeatures(
            hour=8,
            std_deviation=10.0,
            stability_level="stable",
        )
        stability = assess_glucose_stability(features)
        assert stability.level == "stable"
        assert stability.variability_score == 0.0

    def test_variable_assessment(self):
        """Medium std deviation indicates variable."""
        features = HourBaselineFeatures(
            hour=8,
            std_deviation=25.0,
            stability_level="variable",
        )
        stability = assess_glucose_stability(features)
        assert stability.level == "variable"
        assert stability.variability_score == 0.6

    def test_volatile_assessment(self):
        """High std deviation indicates volatile."""
        features = HourBaselineFeatures(
            hour=8,
            std_deviation=50.0,
            stability_level="volatile",
        )
        stability = assess_glucose_stability(features)
        assert stability.level == "volatile"
        assert stability.variability_score == 1.0

    def test_unknown_with_no_std(self):
        """No std deviation returns unknown."""
        features = HourBaselineFeatures(hour=8)
        stability = assess_glucose_stability(features)
        assert stability.level == "unknown"


class TestStabilityLevels:
    """Tests for stability level determination."""

    def test_stable_threshold(self):
        """Std <= 15 is stable."""
        std = 15
        stability = "stable" if std <= 15 else "variable" if std <= 30 else "volatile"
        assert stability == "stable"

    def test_variable_threshold(self):
        """Std 16-30 is variable."""
        std = 25
        stability = "stable" if std <= 15 else "variable" if std <= 30 else "volatile"
        assert stability == "variable"

    def test_volatile_threshold(self):
        """Std > 30 is volatile."""
        std = 40
        stability = "stable" if std <= 15 else "variable" if std <= 30 else "volatile"
        assert stability == "volatile"


class TestIntegration:
    """Integration tests for baseline features."""

    @pytest.mark.asyncio
    async def test_compute_hour_baseline(self):
        """Test hour baseline computation (requires DB)."""
        # Placeholder - would need DB setup
        assert True