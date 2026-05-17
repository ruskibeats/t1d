"""API tests for /api/v1/vitals endpoints."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.db.models import User


class TestVitalsAPI:
    @pytest.mark.asyncio
    async def test_create_vital_entry(self, db_session, test_user):
        from app.api.vitals import create_entry
        from app.vitals.schemas import VitalEntryCreate

        data = VitalEntryCreate(
            spo2_percent=98,
            respiratory_rate=16,
            body_temperature_c=36.5,
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.vitals.get_db", return_value=db_session), \
             patch("app.api.vitals.require_active_user", return_value=test_user):
            response = await create_entry(data=data, user=test_user, db=db_session)

        assert response.spo2_percent == 98
        assert response.respiratory_rate == 16

    @pytest.mark.asyncio
    async def test_list_vitals_entries(self, db_session, test_user):
        from app.api.vitals import create_entry
        from app.vitals.schemas import VitalEntryCreate

        data = VitalEntryCreate(spo2_percent=97, measured_at=datetime.now(timezone.utc))
        with patch("app.api.vitals.get_db", return_value=db_session), \
             patch("app.api.vitals.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        from app.vitals.service import VitalService
        result = await VitalService(db_session).list(user_id=test_user.id)
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_vital_entry(self, db_session, test_user):
        from app.api.vitals import create_entry
        from app.api.vitals import get_entry
        from app.vitals.schemas import VitalEntryCreate

        data = VitalEntryCreate(spo2_percent=99, measured_at=datetime.now(timezone.utc))
        with patch("app.api.vitals.get_db", return_value=db_session), \
             patch("app.api.vitals.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.vitals.get_db", return_value=db_session), \
             patch("app.api.vitals.require_active_user", return_value=test_user):
            response = await get_entry(entry_id=created.id, user=test_user, db=db_session)

        assert response.spo2_percent == 99

    @pytest.mark.asyncio
    async def test_delete_vital_entry(self, db_session, test_user):
        from app.api.vitals import create_entry
        from app.api.vitals import delete_entry
        from app.vitals.schemas import VitalEntryCreate

        data = VitalEntryCreate(spo2_percent=96, measured_at=datetime.now(timezone.utc))
        with patch("app.api.vitals.get_db", return_value=db_session), \
             patch("app.api.vitals.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.vitals.get_db", return_value=db_session), \
             patch("app.api.vitals.require_active_user", return_value=test_user):
            await delete_entry(entry_id=created.id, user=test_user, db=db_session)

        from app.vitals.service import VitalService
        result = await VitalService(db_session).get(user_id=test_user.id, entry_id=created.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_vital_entry(self, db_session, test_user):
        from app.vitals.schemas import VitalEntryCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            VitalEntryCreate(spo2_percent=150, measured_at=datetime.now(timezone.utc))
