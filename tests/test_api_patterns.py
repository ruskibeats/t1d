"""Integration tests for the Pattern API endpoints."""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from app.db.models import GlucoseReading, ContextEvent
from app.models.pattern import PatternType


class TestPatternAPI:
    """Tests for /api/v1/patterns endpoints."""

    @pytest.mark.asyncio
    async def test_analyze_patterns_with_data(self, db_session, test_user):
        """POST /api/v1/patterns/analyze returns analysis with seeded data."""
        from app.api.patterns import analyze_patterns
        from app.models.pattern import PatternAnalysisCreate

        for i in range(24):
            reading = GlucoseReading(
                user_id=test_user.id,
                glucose_value=100.0 + (i % 5) * 20,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            )
            db_session.add(reading)
        await db_session.commit()

        request = PatternAnalysisCreate(
            pattern_type=PatternType.POST_MEAL_SPIKE,
            time_period="daily",
            start_date=datetime.now(timezone.utc) - timedelta(days=1),
            end_date=datetime.now(timezone.utc),
            user_id=test_user.id,
        )

        with patch("app.api.patterns.require_active_user", return_value=test_user), \
             patch("app.api.patterns.get_db", return_value=db_session):
            response = await analyze_patterns(
                analysis_request=request,
                session=db_session,
                user=test_user,
            )

        assert "analysis" in response
        assert "tir" in response["analysis"]
        assert "post_meal_spikes" in response

    @pytest.mark.asyncio
    async def test_analyze_patterns_empty_data(self, db_session, test_user):
        """POST /api/v1/patterns/analyze with no data returns graceful result."""
        from app.api.patterns import analyze_patterns
        from app.models.pattern import PatternAnalysisCreate

        request = PatternAnalysisCreate(
            pattern_type=PatternType.POST_MEAL_SPIKE,
            time_period="daily",
            start_date=datetime.now(timezone.utc) - timedelta(days=1),
            end_date=datetime.now(timezone.utc),
            user_id=test_user.id,
        )

        with patch("app.api.patterns.require_active_user", return_value=test_user), \
             patch("app.api.patterns.get_db", return_value=db_session):
            response = await analyze_patterns(
                analysis_request=request,
                session=db_session,
                user=test_user,
            )

        assert "analysis" in response
        assert response["statistics"]["total"] == 0

    @pytest.mark.asyncio
    async def test_tir_endpoint(self, db_session, test_user):
        """POST /api/v1/patterns/tir returns time-in-range stats."""
        from app.api.patterns import calculate_tir

        for i in range(12):
            reading = GlucoseReading(
                user_id=test_user.id,
                glucose_value=120.0,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            )
            db_session.add(reading)
        await db_session.commit()

        with patch("app.api.patterns.require_active_user", return_value=test_user), \
             patch("app.api.patterns.get_db", return_value=db_session):
            response = await calculate_tir(
                start_date=datetime.now(timezone.utc) - timedelta(days=1),
                end_date=datetime.now(timezone.utc),
                session=db_session,
                user=test_user,
            )

        assert "time_in_range" in response
        assert response["readings"]["total"] >= 12

    @pytest.mark.asyncio
    async def test_spikes_endpoint(self, db_session, test_user):
        """POST /api/v1/patterns/spikes detects post-meal spikes."""
        from app.api.patterns import detect_spikes

        meal = ContextEvent(
            user_id=test_user.id,
            event_type="meal",
            event_subtype="lunch",
            description="Test Meal",
            carbs_grams=60,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
        )
        db_session.add(meal)

        for i in range(6):
            reading = GlucoseReading(
                user_id=test_user.id,
                glucose_value=100.0 + i * 15,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=3, minutes=i * 30),
                reading_type="sensor",
                source="dexcom",
                trend="rising",
            )
            db_session.add(reading)
        await db_session.commit()

        with patch("app.api.patterns.require_active_user", return_value=test_user), \
             patch("app.api.patterns.get_db", return_value=db_session):
            response = await detect_spikes(
                start_date=datetime.now(timezone.utc) - timedelta(days=1),
                end_date=datetime.now(timezone.utc),
                session=db_session,
                user=test_user,
            )

        assert "spikes" in response

    @pytest.mark.asyncio
    async def test_overnight_endpoint(self, db_session, test_user):
        """POST /api/v1/patterns/overnight detects overnight lows."""
        from app.api.patterns import detect_overnight_lows

        reading = GlucoseReading(
            user_id=test_user.id,
            glucose_value=65.0,
            glucose_units="mg/dL",
            timestamp=datetime.now(timezone.utc).replace(hour=3, minute=0, second=0, microsecond=0),
            reading_type="sensor",
            source="dexcom",
            trend="falling",
        )
        db_session.add(reading)
        await db_session.commit()

        with patch("app.api.patterns.require_active_user", return_value=test_user), \
             patch("app.api.patterns.get_db", return_value=db_session):
            response = await detect_overnight_lows(
                start_date=datetime.now(timezone.utc) - timedelta(days=1),
                end_date=datetime.now(timezone.utc),
                session=db_session,
                user=test_user,
            )

        assert "events" in response

    @pytest.mark.asyncio
    async def test_exercise_endpoint(self, db_session, test_user):
        """POST /api/v1/patterns/exercise analyzes exercise impact."""
        from app.api.patterns import analyze_exercise

        exercise = ContextEvent(
            user_id=test_user.id,
            event_type="exercise",
            intensity="moderate",
            duration=45,
            heart_rate_avg=140,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db_session.add(exercise)
        await db_session.commit()

        with patch("app.api.patterns.require_active_user", return_value=test_user), \
             patch("app.api.patterns.get_db", return_value=db_session):
            response = await analyze_exercise(
                start_date=datetime.now(timezone.utc) - timedelta(days=1),
                end_date=datetime.now(timezone.utc),
                session=db_session,
                user=test_user,
            )

        # Response has either "events" or "impacts" key
        assert "events" in response or "impacts" in response
