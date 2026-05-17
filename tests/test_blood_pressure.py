"""Integration tests for Blood Pressure API endpoints."""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from app.db.models import User


class TestBloodPressureAPI:
    """Tests for /api/v1/blood-pressure endpoints."""

    @pytest.mark.asyncio
    async def test_create_bp_entry(self, db_session, test_user):
        """POST /api/v1/blood-pressure creates an entry."""
        from app.api.blood_pressure import create_entry
        from app.blood_pressure.schemas import BloodPressureEntryCreate

        data = BloodPressureEntryCreate(
            systolic=120,
            diastolic=80,
            measured_at=datetime.now(timezone.utc),
            source="manual",
        )

        with patch("app.api.blood_pressure.get_db", return_value=db_session), \
             patch("app.api.blood_pressure.require_active_user", return_value=test_user):
            response = await create_entry(
                data=data,
                user=test_user,
                db=db_session,
            )

        assert response.systolic == 120
        assert response.diastolic == 80

    @pytest.mark.asyncio
    async def test_list_bp_entries(self, db_session, test_user):
        """GET /api/v1/blood-pressure returns list of entries."""
        from app.api.blood_pressure import create_entry, list_entries
        from app.blood_pressure.schemas import BloodPressureEntryCreate

        data = BloodPressureEntryCreate(
            systolic=130,
            diastolic=85,
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.blood_pressure.get_db", return_value=db_session), \
             patch("app.api.blood_pressure.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.blood_pressure.get_db", return_value=db_session), \
             patch("app.api.blood_pressure.require_active_user", return_value=test_user):
            response = await list_entries(
                db=db_session,
                user=test_user,
            )

        assert isinstance(response, list)
        assert len(response) >= 1

    @pytest.mark.asyncio
    async def test_get_bp_entry(self, db_session, test_user):
        """GET /api/v1/blood-pressure/{id} returns entry detail."""
        from app.api.blood_pressure import create_entry, get_entry
        from app.blood_pressure.schemas import BloodPressureEntryCreate

        data = BloodPressureEntryCreate(
            systolic=140,
            diastolic=90,
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.blood_pressure.get_db", return_value=db_session), \
             patch("app.api.blood_pressure.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.blood_pressure.get_db", return_value=db_session), \
             patch("app.api.blood_pressure.require_active_user", return_value=test_user):
            response = await get_entry(
                entry_id=created.id,
                user=test_user,
                db=db_session,
            )

        assert response.systolic == 140
        assert response.diastolic == 90

    @pytest.mark.asyncio
    async def test_delete_bp_entry(self, db_session, test_user):
        """DELETE /api/v1/blood-pressure/{id} removes entry."""
        from app.api.blood_pressure import create_entry, delete_entry
        from app.blood_pressure.schemas import BloodPressureEntryCreate

        data = BloodPressureEntryCreate(
            systolic=110,
            diastolic=70,
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.blood_pressure.get_db", return_value=db_session), \
             patch("app.api.blood_pressure.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.blood_pressure.get_db", return_value=db_session), \
             patch("app.api.blood_pressure.require_active_user", return_value=test_user):
            response = await delete_entry(
                entry_id=created.id,
                user=test_user,
                db=db_session,
            )

        # DELETE returns None (204 No Content)
        assert response is None

    @pytest.mark.asyncio
    async def test_invalid_bp(self, db_session, test_user):
        """POST /api/v1/blood-pressure with invalid systolic returns 422."""
        from pydantic import ValidationError
        from app.blood_pressure.schemas import BloodPressureEntryCreate

        # Pydantic validation fails before reaching the endpoint
        # systolic=-10 violates ge=50 constraint
        with pytest.raises(ValidationError) as exc_info:
            BloodPressureEntryCreate(
                systolic=-10,
                diastolic=80,
                measured_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("systolic",) and e["type"] == "greater_than_equal" for e in errors)

    @pytest.mark.asyncio
    async def test_invalid_diastolic(self, db_session, test_user):
        """POST /api/v1/blood-pressure with invalid diastolic returns 422."""
        from pydantic import ValidationError
        from app.blood_pressure.schemas import BloodPressureEntryCreate

        # diastolic=250 violates le=200 constraint
        with pytest.raises(ValidationError) as exc_info:
            BloodPressureEntryCreate(
                systolic=120,
                diastolic=250,
                measured_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("diastolic",) and e["type"] == "less_than_equal" for e in errors)