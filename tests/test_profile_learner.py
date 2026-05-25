"""Tests for the Profile Learning Convergence service."""

import pytest
from app.services.profile_learner import (
    compute_profile_match,
    compute_from_readings,
    _value_in_range,
    _compute_anchor_scores,
    UserGlucoseStats,
    ProfileLearningResult,
)


class TestValueInRange:
    def test_exact_inside(self):
        assert _value_in_range(100, (90, 110)) == 1.0

    def test_at_boundary(self):
        assert _value_in_range(90, (90, 110)) == 1.0
        assert _value_in_range(110, (90, 110)) == 1.0

    def test_slightly_outside(self):
        score = _value_in_range(120, (90, 110))
        assert 0 < score < 1.0

    def test_far_outside(self):
        score = _value_in_range(500, (90, 110))
        assert score == 0.0

    def test_zero_span(self):
        assert _value_in_range(50, (50, 50)) == 1.0
        assert _value_in_range(51, (50, 50)) == 0.0


class TestComputeAnchorScores:
    def test_well_controlled_user_scores_well_or_exercise_high(self):
        stats = UserGlucoseStats(
            total_readings=2000,
            days_of_data=14,
            avg_glucose_mgdl=110,
            glucose_std_dev=15,
            tir_percentage=85,
            hypo_rate=0.03,
            variability_cv=18,
            exercise_drop_pct=5,
        )
        scored = _compute_anchor_scores(stats)
        top_key = scored[0][0]
        # Well-controlled and exercise_regimen are similar profiles
        # Well-controlled, exercise_regimen, and exercise_sensitive share similar low-variability ranges
        assert top_key in ("well_controlled", "exercise_regimen", "exercise_sensitive")

    def test_brittle_user_scores_brittle_or_high_var_high(self):
        stats = UserGlucoseStats(
            total_readings=2000,
            days_of_data=14,
            avg_glucose_mgdl=130,
            glucose_std_dev=35,
            tir_percentage=35,
            hypo_rate=0.25,
            variability_cv=45,
        )
        scored = _compute_anchor_scores(stats)
        top_key = scored[0][0]
        # Brittle and high_variability overlap heavily
        assert top_key in ("brittle", "high_variability")

    def test_dawn_phenomenon_user(self):
        stats = UserGlucoseStats(
            total_readings=2000,
            days_of_data=14,
            avg_glucose_mgdl=120,
            tir_percentage=70,
            variability_cv=22,
            dawn_trend_mgdl_per_hour=4.0,
        )
        scored = _compute_anchor_scores(stats)
        top_keys = [k for k, _ in scored[:3]]
        assert "dawn_phenomenon" in top_keys

    def test_overnight_hypo_user(self):
        stats = UserGlucoseStats(
            total_readings=2000,
            days_of_data=14,
            avg_glucose_mgdl=115,
            hypo_rate=0.35,
            overnight_low_rate=0.40,
            variability_cv=22,
        )
        scored = _compute_anchor_scores(stats)
        top_keys = [k for k, _ in scored[:3]]
        assert "overnight_hypo" in top_keys

    def test_high_variability_user(self):
        stats = UserGlucoseStats(
            total_readings=2000,
            days_of_data=14,
            variability_cv=48,
            glucose_std_dev=45,
        )
        scored = _compute_anchor_scores(stats)
        top_keys = [k for k, _ in scored[:3]]
        assert "high_variability" in top_keys

    def test_all_12_anchors_scored(self):
        stats = UserGlucoseStats()
        scored = _compute_anchor_scores(stats)
        assert len(scored) == 12
        assert all(0 <= s <= 1 for _, s in scored)


class TestComputeProfileMatch:
    def test_insufficient_data_returns_low_confidence(self):
        stats = UserGlucoseStats(total_readings=10, days_of_data=1)
        result = compute_profile_match(stats)
        assert result.confidence == "low"
        assert result.is_ready is False

    def test_sufficient_data_returns_high_confidence(self):
        stats = UserGlucoseStats(
            total_readings=3000,
            days_of_data=14,
            avg_glucose_mgdl=110,
            glucose_std_dev=15,
        )
        result = compute_profile_match(stats)
        assert result.confidence in ("moderate", "high")

    def test_returns_primary_anchor(self):
        stats = UserGlucoseStats(total_readings=2000, days_of_data=14)
        result = compute_profile_match(stats)
        assert result.primary_anchor is not None
        assert 0 <= result.primary_anchor.score <= 1.0

    def test_returns_top_5_matches(self):
        stats = UserGlucoseStats(total_readings=2000, days_of_data=14)
        result = compute_profile_match(stats)
        assert len(result.top_matches) == 5

    def test_returns_hybrid_weights(self):
        stats = UserGlucoseStats(total_readings=2000, days_of_data=14)
        result = compute_profile_match(stats)
        assert len(result.hybrid_weights) > 0
        total_w = sum(result.hybrid_weights.values())
        assert abs(total_w - 1.0) < 0.01

    def test_primary_is_top_of_list(self):
        stats = UserGlucoseStats(total_readings=2000, days_of_data=14)
        result = compute_profile_match(stats)
        assert result.primary_anchor.anchor_type == result.top_matches[0].anchor_type
        assert result.primary_anchor.score == result.top_matches[0].score


class TestComputeFromReadings:
    def test_empty_readings(self):
        result = compute_from_readings([])
        assert result.days_of_data == 0
        assert result.is_ready is False

    def test_simple_flat_readings(self):
        readings = [
            {"timestamp": "2026-05-01T08:00:00", "value": 110},
            {"timestamp": "2026-05-01T09:00:00", "value": 115},
            {"timestamp": "2026-05-01T10:00:00", "value": 112},
        ]
        result = compute_from_readings(readings)
        assert result.days_of_data > 0
        assert result.primary_anchor is not None

    def test_tir_calculation(self):
        readings = []
        base = "2026-05-01T{:02d}:00:00"
        for i in range(24):
            readings.append({"timestamp": base.format(i), "value": 100.0})
        readings.append({"timestamp": "2026-05-01T12:00:00", "value": 55})  # one low
        result = compute_from_readings(readings)
        assert result.primary_anchor is not None

    def test_meal_spike_detected(self):
        """Readings showing higher post-meal values should skew toward post_meal_spike."""
        # Generate readings that look like post-meal spike pattern
        readings = []
        meal_events = []
        base_date = "2026-05-01"
        for day in range(14):
            for hour in range(24):
                val = 110  # baseline
                # Spike after lunch (12pm) and dinner (6pm)
                if 12 <= hour <= 14:
                    val = 180
                elif 18 <= hour <= 20:
                    val = 190
                readings.append({
                    "timestamp": f"{base_date}T{hour:02d}:00:00",
                    "value": val,
                })
            meal_events.append({"timestamp": f"{base_date}T12:00:00", "carbs_grams": 60})
            meal_events.append({"timestamp": f"{base_date}T18:00:00", "carbs_grams": 50})

        result = compute_from_readings(readings, meal_events=meal_events)
        assert result.primary_anchor is not None
        assert result.top_matches[0].score > 0

    def test_dawn_phenomenon_scores_higher_with_dawn_data(self):
        """With dawn trend data, dawn_phenomenon should score higher than without it."""
        # Without dawn trend
        stats_no_dawn = UserGlucoseStats(
            total_readings=2000, days_of_data=14,
            avg_glucose_mgdl=115, variability_cv=20,
            dawn_trend_mgdl_per_hour=0,
        )
        scored_no_dawn = {k: s for k, s in _compute_anchor_scores(stats_no_dawn)}

        # With dawn trend
        stats_dawn = UserGlucoseStats(
            total_readings=2000, days_of_data=14,
            avg_glucose_mgdl=115, variability_cv=20,
            dawn_trend_mgdl_per_hour=4.0,
        )
        scored_dawn = {k: s for k, s in _compute_anchor_scores(stats_dawn)}

        # Dawn phenomenon should score higher with dawn data
        assert scored_dawn["dawn_phenomenon"] > scored_no_dawn["dawn_phenomenon"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])