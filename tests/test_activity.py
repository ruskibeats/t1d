"""API tests for /api/v1/activity endpoints."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.db.models import User


class TestActivityAPI:
    @pytest.mark.asyncio
    async def test_create_activity_entry(self, db_session, test_user):
        from app.api.activity import create_entry
        from app.activity.schemas import ActivityEntryCreate

        data = ActivityEntryCreate(
            steps=5000,
            distance_km=3.5,
            floors_climbed=10,
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.activity.get_db", return_value=db_session), \
             patch("app.api.activity.require_active_user", return_value=test_user):
            response = await create_entry(data=data, user=test_user, db=db_session)

        assert response.steps == 5000
        assert response.distance_km == 3.5
        assert response.floors_climbed == 10

    @pytest.mark.asyncio
    async def test_list_activity_entries(self, db_session, test_user):
        from app.api.activity import create_entry
        from app.activity.schemas import ActivityEntryCreate

        data = ActivityEntryCreate(steps=1000, measured_at=datetime.now(timezone.utc))
        with patch("app.api.activity.get_db", return_value=db_session), \
             patch("app.api.activity.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        from app.activity.service import ActivityService
        result = await ActivityService(db_session).list(user_id=test_user.id)
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_activity_entry(self, db_session, test_user):
        from app.api.activity import create_entry
        from app.api.activity import get_entry
        from app.activity.schemas import ActivityEntryCreate

        data = ActivityEntryCreate(steps=2000, measured_at=datetime.now(timezone.utc))
        with patch("app.api.activity.get_db", return_value=db_session), \
             patch("app.api.activity.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.activity.get_db", return_value=db_session), \
             patch("app.api.activity.require_active_user", return_value=test_user):
            response = await get_entry(entry_id=created.id, user=test_user, db=db_session)

        assert response.steps == 2000

    @pytest.mark.asyncio
    async def test_delete_activity_entry(self, db_session, test_user):
        from app.api.activity import create_entry
        from app.api.activity import delete_entry
        from app.activity.schemas import ActivityEntryCreate

        data = ActivityEntryCreate(steps=500, measured_at=datetime.now(timezone.utc))
        with patch("app.api.activity.get_db", return_value=db_session), \
             patch("app.api.activity.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.activity.get_db", return_value=db_session), \
             patch("app.api.activity.require_active_user", return_value=test_user):
            await delete_entry(entry_id=created.id, user=test_user, db=db_session)

        from app.activity.service import ActivityService
        result = await ActivityService(db_session).get(user_id=test_user.id, entry_id=created.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_activity_entry(self, db_session, test_user):
        from app.activity.schemas import ActivityEntryCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ActivityEntryCreate(steps=-100, measured_at=datetime.now(timezone.utc))
