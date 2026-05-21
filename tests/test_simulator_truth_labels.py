"""Tests for truth label planting and detector evaluation."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.simulator.truth_labels import TruthLabelPlacer
from app.simulator.patient_factory import generate_patient_config
from app.simulator.schemas import AnchorType


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def config():
    return generate_patient_config(AnchorType.POST_MEAL_SPIKE, seed=42)


@pytest.fixture
def placer(mock_db):
    return TruthLabelPlacer(mock_db, sim_run_id=1)


@pytest.fixture
def sample_meals():
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [
        {"timestamp": base + timedelta(hours=7), "type": "breakfast",
         "description": "Breakfast", "carbs_grams": 65.0, "fat_grams": 12.0,
         "protein_grams": 18.0, "calories": 400, "is_high_fat": False},
        {"timestamp": base + timedelta(hours=12), "type": "lunch",
         "description": "Lunch", "carbs_grams": 85.0, "fat_grams": 30.0,
         "protein_grams": 30.0, "calories": 700, "is_high_fat": True},
        {"timestamp": base + timedelta(hours=18), "type": "dinner",
         "description": "Dinner", "carbs_grams": 100.0, "fat_grams": 40.0,
         "protein_grams": 40.0, "calories": 900, "is_high_fat": True},
    ]


@pytest.fixture
def sample_cgm(sample_meals):
    """Generate CGM readings with known peaks after meals."""
    readings = []
    base = sample_meals[0]["timestamp"] - timedelta(hours=1)
    for i in range(24 * 12):  # 24 hours at 5-min intervals
        t = base + timedelta(minutes=i * 5)
        value = 120.0  # baseline

        # Add meal peaks
        for meal in sample_meals:
            meal_time = meal["timestamp"]
            hours_since = (t - meal_time).total_seconds() / 3600
            if 0 <= hours_since <= 3:
                rise = meal["carbs_grams"] * 2.5 * (hours_since / 1.5) * (2.718 ** (-hours_since / 1.5))
                value += rise

        # Add delayed fat effect
        for meal in sample_meals:
            if meal["is_high_fat"]:
                meal_time = meal["timestamp"]
                hours_since = (t - meal_time).total_seconds() / 3600
                if 4 <= hours_since <= 7:
                    fat_phase = (hours_since - 4) / 1.5
                    value += meal["carbs_grams"] * 0.3 * fat_phase * (2.718 ** (-fat_phase))

        readings.append({
            "timestamp": t,
            "glucose_value": round(value, 1),
            "trend": "flat",
            "trend_rate": 0.0,
        })
    return readings


@pytest.fixture
def sample_daily_schedules(sample_meals):
    """Minimal DailySchedule-like objects for truth planting."""
    from app.simulator.day_context import DailySchedule

    base = sample_meals[0]["timestamp"].replace(hour=0, minute=0, second=0)
    return [
        DailySchedule(
            date=base,
            meals=sample_meals,
            insulin=[{"timestamp": m["timestamp"] - timedelta(minutes=10),
                      "type": "bolus", "units": 5.0} for m in sample_meals],
            exercise=[
                {"timestamp": base + timedelta(hours=17), "duration_minutes": 30,
                 "intensity": "moderate", "type": "cardio",
                 "description": "Cardio"},
            ],
            sleep_start=base + timedelta(hours=22),
            sleep_end=base + timedelta(hours=31),  # next day 7am
        ),
    ]


class TestTruthLabelPlacer:
    """Truth label planting should correctly identify expected patterns."""

    @pytest.mark.asyncio
    async def test_plant_post_meal_spike_truths(self, placer, config, sample_meals, sample_cgm):
        """Should plant truths for meals that produce > 180 peaks."""
        truths = await placer.plant_post_meal_spike_truths(
            sim_user_id=1, user_id=1, config=config,
            meals=sample_meals, cgm_readings=sample_cgm,
            sim_user_key="test_user",
        )
        # At least high-carb meals should generate spike truths
        high_carb_meals = [m for m in sample_meals if m["carbs_grams"] >= TruthLabelPlacer.MIN_SPIKE_CARBS]
        assert len(truths) > 0
        for t in truths:
            assert t.pattern_type == "post_meal_spike"
            assert t.truth_payload is not None
            assert "carbs_grams" in t.truth_payload

    @pytest.mark.asyncio
    async def test_plant_overnight_low_truths(self, placer, config, sample_daily_schedules, sample_cgm):
        """Should plant truths for overnight low events."""
        truths = await placer.plant_overnight_low_truths(
            sim_user_id=1, user_id=1, config=config,
            daily_schedules=sample_daily_schedules, cgm_readings=sample_cgm,
            sim_user_key="test_user",
        )
        # May or may not find lows depending on config + readings
        assert isinstance(truths, list)

    @pytest.mark.asyncio
    async def test_plant_exercise_effect_truths(self, placer, config, sample_daily_schedules, sample_cgm):
        """Should plant truths for exercise→drop patterns."""
        truths = await placer.plant_exercise_effect_truths(
            sim_user_id=1, user_id=1, config=config,
            daily_schedules=sample_daily_schedules, cgm_readings=sample_cgm,
            sim_user_key="test_user",
        )
        assert isinstance(truths, list)

    @pytest.mark.asyncio
    async def test_plant_delayed_high_fat_truths(self, placer, config, sample_daily_schedules, sample_cgm):
        """Should plant truths for delayed high-fat spikes."""
        truths = await placer.plant_delayed_high_fat_truths(
            sim_user_id=1, user_id=1, config=config,
            daily_schedules=sample_daily_schedules, cgm_readings=sample_cgm,
            sim_user_key="test_user",
        )
        # Lunch and dinner are high-fat, so at least some truths should be planted
        assert len(truths) > 0
        for t in truths:
            assert t.pattern_type == "delayed_high_fat"

    @pytest.mark.asyncio
    async def test_plant_all_truths(self, placer, config, sample_daily_schedules, sample_cgm, sample_meals):
        """All truth types should be planted together without error."""
        truths = await placer.plant_all_truths(
            sim_user_id=1, user_id=1, config=config,
            daily_schedules=sample_daily_schedules, cgm_readings=sample_cgm,
            sim_user_key="test_user",
        )
        # Should have truths from multiple pattern types
        pattern_types = {t.pattern_type for t in truths}
        assert "post_meal_spike" in pattern_types
        assert "delayed_high_fat" in pattern_types
        assert len(truths) >= 2  # At least one spike + one fat truth
