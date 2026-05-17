"""Integration tests for the Glucose API endpoints."""

import pytest
from datetime import datetime, timezone, timedelta

from app.db.models import GlucoseReading


class TestGlucoseAPI:
    """Tests for /api/v1/glucose endpoints."""

    @pytest.mark.asyncio
    async def test_list_glucose_readings(self, db_session, test_user):
        """GET /api/v1/glucose returns seeded readings."""
        from app.api.glucose import get_glucose_readings

        for i in range(5):
            reading = GlucoseReading(
                user_id=test_user.id,
                glucose_value=100.0 + i * 10,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            )
            db_session.add(reading)
        await db_session.commit()

        response = await get_glucose_readings(
            start_time=None,
            end_time=None,
            limit=100,
            skip=0,
            session=db_session,
            user=test_user,
        )

        assert isinstance(response, list)
        assert len(response) >= 5

    @pytest.mark.asyncio
    async def test_create_glucose_reading(self, db_session, test_user):
        """POST /api/v1/glucose creates a reading."""
        from app.api.glucose import create_glucose_reading
        from app.models.glucose import GlucoseReadingCreate

        data = GlucoseReadingCreate(
            glucose_value=120.0,
            glucose_units="mg/dL",
            timestamp=datetime.now(timezone.utc),
            reading_type="fingerstick",
            source="manual",
            trend="Flat",
        )

        response = await create_glucose_reading(
            reading_data=data,
            session=db_session,
            user=test_user,
        )

        assert response.glucose_value == 120.0
        assert response.reading_type == "fingerstick"
        assert response.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_latest_glucose(self, db_session, test_user):
        """GET /api/v1/glucose/latest returns most recent reading."""
        from app.api.glucose import get_latest_glucose

        for i in range(3):
            reading = GlucoseReading(
                user_id=test_user.id,
                glucose_value=100.0 + i * 20,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            )
            db_session.add(reading)
        await db_session.commit()

        response = await get_latest_glucose(
            session=db_session,
            user=test_user,
        )

        assert response is not None
        assert response.glucose_value == 100.0

    @pytest.mark.asyncio
    async def test_get_glucose_reading_detail(self, db_session, test_user):
        """GET /api/v1/glucose/{id} returns reading detail."""
        from app.api.glucose import get_glucose_reading

        reading = GlucoseReading(
            user_id=test_user.id,
            glucose_value=150.0,
            glucose_units="mg/dL",
            timestamp=datetime.now(timezone.utc),
            reading_type="sensor",
            source="dexcom",
            trend="flat",
        )
        db_session.add(reading)
        await db_session.commit()
        await db_session.refresh(reading)

        response = await get_glucose_reading(
            reading_id=reading.id,
            session=db_session,
            user=test_user,
        )

        assert response.glucose_value == 150.0
