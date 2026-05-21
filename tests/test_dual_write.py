"""Tests verifying dual-write from domain tables to health_metrics."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app.db.models import User


class TestDualWrite:
    """Verify that creating domain entries also writes to health_metrics."""

    @pytest.mark.asyncio
    async def test_exercise_dual_write(self, db_session, test_user):
        """POST /api/v1/exercise should create a row in health_metrics with type EXERCISE_MINUTES."""
        from app.api.exercise import create_entry
        from app.exercise.schemas import ExerciseEntryCreate
        from app.metrics.models import HealthMetric
        from app.metrics.types import MetricType
        from sqlalchemy import select

        data = ExerciseEntryCreate(
            type="running",
            start_time=datetime.now(timezone.utc),
            duration_minutes=30,
            calories=250,
        )
        with patch("app.api.exercise.get_db", return_value=db_session), \
             patch("app.api.exercise.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        result = await db_session.execute(
            select(HealthMetric).where(
                HealthMetric.user_id == test_user.id,
                HealthMetric.type == MetricType.EXERCISE_MINUTES,
            )
        )
        metric = result.scalar_one_or_none()
        assert metric is not None
        assert metric.value == 30
        assert metric.unit == "minutes"

    @pytest.mark.asyncio
    async def test_food_dual_write(self, db_session, test_user):
        """POST /api/v1/food/entries should create a row in health_metrics with type CALORIES."""
        from app.api.food import create_entry
        from app.food.schemas import FoodEntryCreate
        from app.metrics.models import HealthMetric
        from app.metrics.types import MetricType
        from sqlalchemy import select

        data = FoodEntryCreate(
            quantity=1,
            unit="serving",
            entry_date=datetime.now(timezone.utc),
            meal_type="lunch",
            calories=500,
            protein=30,
            carbs=60,
            fat=15,
        )
        with patch("app.api.food.get_db", return_value=db_session), \
             patch("app.api.food.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        result = await db_session.execute(
            select(HealthMetric).where(
                HealthMetric.user_id == test_user.id,
                HealthMetric.type == MetricType.CALORIES,
            )
        )
        metric = result.scalar_one_or_none()
        assert metric is not None
        assert metric.value == 500

    @pytest.mark.asyncio
    async def test_sleep_dual_write(self, db_session, test_user):
        """POST /api/v1/sleep should create a row in health_metrics with type SLEEP_HOURS."""
        from app.sleep.service import SleepService
        from app.sleep.schemas import SleepEntryCreate
        from app.metrics.models import HealthMetric
        from app.metrics.types import MetricType
        from sqlalchemy import select

        now = datetime.now(timezone.utc)
        data = SleepEntryCreate(
            start_time=now,
            end_time=now,
            duration_minutes=480,
            quality_score=85,
        )
        await SleepService(db_session).create(user_id=test_user.id, data=data)

        result = await db_session.execute(
            select(HealthMetric).where(
                HealthMetric.user_id == test_user.id,
                HealthMetric.type == MetricType.SLEEP_HOURS,
            )
        )
        metric = result.scalar_one_or_none()
        assert metric is not None
        assert metric.value == 8.0
