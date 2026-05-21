"""Integration tests for the Sleep API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from app.db.models import User


class TestSleepAPI:
    """Tests for /api/v1/sleep endpoints."""

    @pytest.mark.asyncio
    async def test_create_sleep_entry(self, db_session, test_user):
        """POST /api/v1/sleep creates a sleep entry."""
        from app.api.sleep import create_entry
        from app.sleep.schemas import SleepEntryCreate

        data = SleepEntryCreate(
            start_time=datetime.now(timezone.utc) - timedelta(hours=8),
            end_time=datetime.now(timezone.utc),
            duration_minutes=480,
            quality_score=85,
        )

        with patch("app.api.sleep.get_db", return_value=db_session):
            response = await create_entry(
                data=data,
                user_id=test_user.id,
                db=db_session,
            )

        assert response.duration_minutes == 480
        assert response.quality_score == 85

    @pytest.mark.asyncio
    async def test_list_sleep_entries(self, db_session, test_user):
        """GET /api/v1/sleep returns list of entries."""
        from app.api.sleep import list_entries, create_entry
        from app.sleep.schemas import SleepEntryCreate

        data = SleepEntryCreate(
            start_time=datetime.now(timezone.utc) - timedelta(hours=16),
            end_time=datetime.now(timezone.utc) - timedelta(hours=8),
            duration_minutes=480,
        )
        with patch("app.api.sleep.get_db", return_value=db_session):
            await create_entry(data=data, user_id=test_user.id, db=db_session)

        # Use service directly
        from app.sleep.service import SleepService
        response = await SleepService(db_session).list(user_id=test_user.id)

        assert isinstance(response, list)

    @pytest.mark.asyncio
    async def test_get_sleep_detail(self, db_session, test_user):
        """GET /api/v1/sleep/{id} returns entry detail."""
        from app.api.sleep import create_entry, get_entry
        from app.sleep.schemas import SleepEntryCreate

        data = SleepEntryCreate(
            start_time=datetime.now(timezone.utc) - timedelta(hours=8),
            end_time=datetime.now(timezone.utc),
            duration_minutes=480,
        )
        with patch("app.api.sleep.get_db", return_value=db_session):
            created = await create_entry(data=data, user_id=test_user.id, db=db_session)

        with patch("app.api.sleep.get_db", return_value=db_session):
            response = await get_entry(
                entry_id=created.id,
                user_id=test_user.id,
                db=db_session,
            )

        assert response.duration_minutes == 480
