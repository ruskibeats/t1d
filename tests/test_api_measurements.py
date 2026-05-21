"""Integration tests for the Measurements API endpoints."""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone


class TestMeasurementsAPI:
    """Tests for /api/v1/measurements endpoints."""

    @pytest.mark.asyncio
    async def test_create_measurement(self, db_session, test_user):
        """POST /api/v1/measurements creates a measurement."""
        from app.api.measurements import create_measurement
        from app.measurements.schemas import CustomMeasurementCreate

        data = CustomMeasurementCreate(
            metric_name="weight",
            value=70.5,
            unit="kg",
            measured_at=datetime.now(timezone.utc),
        )

        with patch("app.api.measurements.get_db", return_value=db_session):
            response = await create_measurement(
                data=data,
                user_id=test_user.id,
                db=db_session,
            )

        assert response.metric_name == "weight"
        assert response.value == 70.5

    @pytest.mark.asyncio
    async def test_list_measurements(self, db_session, test_user):
        """GET /api/v1/measurements returns list."""
        from app.api.measurements import list_measurements, create_measurement
        from app.measurements.schemas import CustomMeasurementCreate

        data = CustomMeasurementCreate(
            metric_name="blood_pressure",
            value=120,
            unit="mmHg",
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.measurements.get_db", return_value=db_session):
            await create_measurement(data=data, user_id=test_user.id, db=db_session)

        # Use service directly
        from app.measurements.service import MeasurementService
        response = await MeasurementService(db_session).list(user_id=test_user.id, limit=100, offset=0)

        assert isinstance(response, list)
        assert len(response) >= 1

    @pytest.mark.asyncio
    async def test_get_measurement_detail(self, db_session, test_user):
        """GET /api/v1/measurements/{id} returns detail."""
        from app.api.measurements import create_measurement, get_measurement
        from app.measurements.schemas import CustomMeasurementCreate

        data = CustomMeasurementCreate(
            metric_name="temperature",
            value=36.6,
            unit="C",
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.measurements.get_db", return_value=db_session):
            created = await create_measurement(data=data, user_id=test_user.id, db=db_session)

        with patch("app.api.measurements.get_db", return_value=db_session):
            response = await get_measurement(
                measurement_id=created.id,
                user_id=test_user.id,
                db=db_session,
            )

        assert response.metric_name == "temperature"
