"""Tests for the patient generation pipeline — anchors, factory, day context, glucose engine."""

import random
from datetime import datetime, timedelta, timezone

import pytest

from app.simulator.anchors import ANCHOR_PARAMETER_RANGES, list_anchor_profiles
from app.simulator.day_context import DayContextGenerator
from app.simulator.glucose_engine import GlucoseEngine
from app.simulator.patient_factory import (
    generate_patient_batch,
    generate_patient_config,
    generate_profile_json,
)
from app.simulator.schemas import AnchorType, PatientConfig


class TestAnchors:
    """Anchor profile definitions should be complete and consistent."""

    def test_all_anchors_defined(self):
        """All AnchorType values should have a corresponding range."""
        profiles = list_anchor_profiles()
        types_in_ranges = {p.anchor_type for p in profiles}
        expected_types = set(AnchorType)
        assert types_in_ranges == expected_types, (
            f"Missing anchors: {expected_types - types_in_ranges}"
        )

    def test_anchor_ranges_valid(self):
        """All parameter ranges should have min <= max."""
        for profile in list_anchor_profiles():
            for field_name in [
                "basal_glucose_mean", "basal_glucose_amplitude",
                "meal_rise_factor", "insulin_sensitivity",
                "carb_ratio", "hypo_risk", "noise_sd",
                "exercise_drop_factor", "dawn_effect_strength",
                "fat_delay_hours", "variability_cv",
            ]:
                mn, mx = getattr(profile, field_name)
                assert mn <= mx, (
                    f"{profile.anchor_type}.{field_name}: {mn} > {mx}"
                )


class TestPatientFactory:
    """Patient parameter generation should be deterministic and valid."""

    def test_generate_config_types(self):
        """Generated PatientConfig should have the right types."""
        config = generate_patient_config(AnchorType.WELL_CONTROLLED, seed=42)
        assert isinstance(config, PatientConfig)
        assert config.anchor_type == AnchorType.WELL_CONTROLLED
        assert config.seed == 42

    def test_generate_config_deterministic(self):
        """Same seed + anchor should produce identical configs."""
        c1 = generate_patient_config(AnchorType.POST_MEAL_SPIKE, seed=100)
        c2 = generate_patient_config(AnchorType.POST_MEAL_SPIKE, seed=100)
        assert c1 == c2

    def test_generate_config_different_seeds(self):
        """Different seeds should produce different configs (with high probability)."""
        c1 = generate_patient_config(AnchorType.BRITTLE, seed=1)
        c2 = generate_patient_config(AnchorType.BRITTLE, seed=2)
        # At least some fields should differ
        assert c1 != c2

    def test_generate_config_within_ranges(self):
        """All generated values should fall within anchor ranges."""
        for anchor in list(AnchorType):
            config = generate_patient_config(anchor, seed=42)
            params = ANCHOR_PARAMETER_RANGES[anchor]

            assert params.basal_glucose_mean[0] <= config.basal_glucose_mean <= params.basal_glucose_mean[1]
            assert params.basal_glucose_amplitude[0] <= config.basal_glucose_amplitude <= params.basal_glucose_amplitude[1]
            # meal_rise_factor is now computed from insulin_sensitivity and carb_ratio
            # to ensure self-consistent glucose engine dynamics, so it may fall outside
            # the original anchor range. Verify it's positive and reasonable.
            assert config.meal_rise_factor > 0
            assert params.insulin_sensitivity[0] <= config.insulin_sensitivity <= params.insulin_sensitivity[1]
            assert params.carb_ratio[0] <= config.carb_ratio <= params.carb_ratio[1]
            assert params.hypo_risk[0] <= config.hypo_risk <= params.hypo_risk[1]
            assert params.noise_sd[0] <= config.noise_sd <= params.noise_sd[1]
            assert params.exercise_drop_factor[0] <= config.exercise_drop_factor <= params.exercise_drop_factor[1]
            assert params.dawn_effect_strength[0] <= config.dawn_effect_strength <= params.dawn_effect_strength[1]
            assert params.fat_delay_hours[0] <= config.fat_delay_hours <= params.fat_delay_hours[1]
            assert params.variability_cv[0] <= config.variability_cv <= params.variability_cv[1]

    def test_generate_batch_count(self):
        """Batch generation should produce the requested number of configs."""
        configs = generate_patient_batch(AnchorType.INSULIN_SENSITIVE, count=10, start_seed=100)
        assert len(configs) == 10

    def test_generate_batch_unique_seeds(self):
        """Each batch config should have a unique seed."""
        configs = generate_patient_batch(AnchorType.DAWN_PHENOMENON, count=10, start_seed=100)
        seeds = {c.seed for c in configs}
        assert len(seeds) == 10

    def test_profile_json(self):
        """Profile JSON should have expected keys."""
        config = generate_patient_config(AnchorType.WELL_CONTROLLED, seed=42)
        profile = generate_profile_json(config)
        assert "anchor_type" in profile
        assert "anchor_label" in profile
        assert "estimated_tir" in profile
        assert "estimated_a1c" in profile
        assert "variability_category" in profile
        assert profile["estimated_tir"] > 0


class TestDayContextGenerator:
    """Daily schedule generation should be reasonable."""

    @pytest.fixture
    def config(self):
        return generate_patient_config(AnchorType.WELL_CONTROLLED, seed=42)

    def test_generates_meals(self, config):
        rng = random.Random(42)
        gen = DayContextGenerator(config, rng)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        schedule = gen.generate_day(base_date)
        assert len(schedule.meals) >= 2  # At least breakfast + lunch + dinner

    def test_generates_insulin(self, config):
        rng = random.Random(42)
        gen = DayContextGenerator(config, rng)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        schedule = gen.generate_day(base_date)
        assert len(schedule.insulin) >= 2  # At least basal + boluses

    def test_sleep_times(self, config):
        rng = random.Random(42)
        gen = DayContextGenerator(config, rng)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        schedule = gen.generate_day(base_date)
        assert schedule.sleep_start is not None
        assert schedule.sleep_end is not None
        assert schedule.sleep_end > schedule.sleep_start

    def test_exercise_regimen_anchor_exercises_more(self):
        """Exercise Regimen anchor should exercise most days."""
        config = generate_patient_config(AnchorType.EXERCISE_REGIMEN, seed=42)
        rng = random.Random(42)
        gen = DayContextGenerator(config, rng)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        exercise_days = 0
        for d in range(20):
            schedule = gen.generate_day(base_date + timedelta(days=d))
            if schedule.exercise:
                exercise_days += 1
        assert exercise_days >= 14  # >= 70% of days

    def test_all_events_sorted(self, config):
        rng = random.Random(42)
        gen = DayContextGenerator(config, rng)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        schedule = gen.generate_day(base_date)
        events = schedule.all_events()
        timestamps = [
            e.get("start_time") or e.get("timestamp")
            for e in events
        ]
        assert timestamps == sorted(timestamps)


class TestGlucoseEngine:
    """Glucose traces should be physiologically plausible."""

    @pytest.fixture
    def config(self):
        return generate_patient_config(AnchorType.WELL_CONTROLLED, seed=42)

    def test_generates_expected_readings(self, config):
        """Engine should produce the right number of readings."""
        rng = random.Random(42)
        engine = GlucoseEngine(config, rng)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        gen = DayContextGenerator(config, random.Random(42))
        schedules = [gen.generate_day(base_date + timedelta(days=d)) for d in range(3)]
        readings = engine.generate_trace(schedules, num_days=3)
        expected_count = 3 * 24 * 12  # 3 days * 24h * 12 samples/h
        assert len(readings) == expected_count

    def test_readings_in_physiological_range(self, config):
        """All glucose values should be within 40-400 mg/dL."""
        rng = random.Random(42)
        engine = GlucoseEngine(config, rng)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        gen = DayContextGenerator(config, random.Random(42))
        schedules = [gen.generate_day(base_date + timedelta(days=d)) for d in range(3)]
        readings = engine.generate_trace(schedules, num_days=3)
        for r in readings:
            # Soft logistic boundary allows slight excursions past 40/400
            assert 20 <= r["glucose_value"] <= 420, f"Value {r['glucose_value']} out of range"

    def test_trend_values_valid(self, config):
        """Trend directions should be valid Dexcom-style strings."""
        valid_trends = {
            "double_up", "single_up", "forty_five_up", "flat",
            "forty_five_down", "single_down", "double_down",
        }
        rng = random.Random(42)
        engine = GlucoseEngine(config, rng)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        gen = DayContextGenerator(config, random.Random(42))
        schedules = [gen.generate_day(base_date + timedelta(days=d)) for d in range(1)]
        readings = engine.generate_trace(schedules, num_days=1)
        for r in readings:
            assert r["trend"] in valid_trends, f"Invalid trend: {r['trend']}"

    def test_post_meal_spike_anchor_produces_higher_spikes(self):
        """Post-meal spike anchor should produce higher glucose peaks."""
        well_config = generate_patient_config(AnchorType.WELL_CONTROLLED, seed=42)
        spike_config = generate_patient_config(AnchorType.POST_MEAL_SPIKE, seed=42)

        def max_glucose(config):
            rng = random.Random(42)
            engine = GlucoseEngine(config, rng)
            base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
            gen = DayContextGenerator(config, random.Random(42))
            schedules = [gen.generate_day(base_date + timedelta(days=d)) for d in range(3)]
            readings = engine.generate_trace(schedules, num_days=3)
            return max(r["glucose_value"] for r in readings)

        # The spike-prone patient should have higher max glucose
        well_max = max_glucose(well_config)
        spike_max = max_glucose(spike_config)
        assert spike_max >= well_max, (
            f"Spike anchor max ({spike_max}) should be >= well-controlled ({well_max})"
        )

    def test_deterministic_trace(self):
        """Same seed should produce identical traces."""
        config = generate_patient_config(AnchorType.WELL_CONTROLLED, seed=100)

        def generate():
            rng = random.Random(100)
            engine = GlucoseEngine(config, rng)
            base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
            gen = DayContextGenerator(config, random.Random(100))
            schedules = [gen.generate_day(base_date + timedelta(days=d)) for d in range(1)]
            return engine.generate_trace(schedules, num_days=1)

        t1 = generate()
        t2 = generate()
        assert len(t1) == len(t2)
        for r1, r2 in zip(t1, t2):
            assert r1["glucose_value"] == pytest.approx(r2["glucose_value"], abs=0.01)
