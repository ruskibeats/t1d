"""API tests for /api/v1/body-battery endpoints."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app.db.models import User


class TestBodyBatteryAPI:
    @pytest.mark.asyncio
    async def test_create_body_battery_entry(self, db_session, test_user):
        from app.api.body_battery import create_entry
        from app.body_battery.schemas import BodyBatteryEntryCreate

        data = BodyBatteryEntryCreate(
            value=75,
            change=5,
            charged=10,
            drained=5,
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.body_battery.get_db", return_value=db_session), \
             patch("app.api.body_battery.require_active_user", return_value=test_user):
            response = await create_entry(data=data, user=test_user, db=db_session)

        assert response.value == 75
        assert response.change == 5

    @pytest.mark.asyncio
    async def test_list_body_battery_entries(self, db_session, test_user):
        from app.api.body_battery import create_entry
        from app.body_battery.schemas import BodyBatteryEntryCreate

        data = BodyBatteryEntryCreate(value=80, measured_at=datetime.now(timezone.utc))
        with patch("app.api.body_battery.get_db", return_value=db_session), \
             patch("app.api.body_battery.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        from app.body_battery.service import BodyBatteryService
        result = await BodyBatteryService(db_session).list(user_id=test_user.id)
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_body_battery_entry(self, db_session, test_user):
        from app.api.body_battery import create_entry
        from app.api.body_battery import get_entry
        from app.body_battery.schemas import BodyBatteryEntryCreate

        data = BodyBatteryEntryCreate(value=60, measured_at=datetime.now(timezone.utc))
        with patch("app.api.body_battery.get_db", return_value=db_session), \
             patch("app.api.body_battery.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.body_battery.get_db", return_value=db_session), \
             patch("app.api.body_battery.require_active_user", return_value=test_user):
            response = await get_entry(entry_id=created.id, user=test_user, db=db_session)

        assert response.value == 60

    @pytest.mark.asyncio
    async def test_delete_body_battery_entry(self, db_session, test_user):
        from app.api.body_battery import create_entry
        from app.api.body_battery import delete_entry
        from app.body_battery.schemas import BodyBatteryEntryCreate

        data = BodyBatteryEntryCreate(value=50, measured_at=datetime.now(timezone.utc))
        with patch("app.api.body_battery.get_db", return_value=db_session), \
             patch("app.api.body_battery.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.body_battery.get_db", return_value=db_session), \
             patch("app.api.body_battery.require_active_user", return_value=test_user):
            await delete_entry(entry_id=created.id, user=test_user, db=db_session)

        from app.body_battery.service import BodyBatteryService
        result = await BodyBatteryService(db_session).get(user_id=test_user.id, entry_id=created.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_body_battery_entry(self, db_session, test_user):
        from app.body_battery.schemas import BodyBatteryEntryCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BodyBatteryEntryCreate(value=150, measured_at=datetime.now(timezone.utc))
