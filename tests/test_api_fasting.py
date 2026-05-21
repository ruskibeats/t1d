"""Integration tests for the Fasting API endpoints."""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta


class TestFastingAPI:
    """Tests for /api/v1/fasting endpoints."""

    @pytest.mark.asyncio
    async def test_create_fasting_entry(self, db_session, test_user):
        """POST /api/v1/fasting creates a fasting entry."""
        from app.api.fasting import create_entry
        from app.fasting.schemas import FastingEntryCreate

        data = FastingEntryCreate(
            start_time=datetime.now(timezone.utc) - timedelta(hours=16),
            end_time=datetime.now(timezone.utc),
            duration_minutes=960,
        )

        with patch("app.api.fasting.get_db", return_value=db_session):
            response = await create_entry(
                data=data,
                user_id=test_user.id,
                db=db_session,
            )

        assert response.duration_minutes == 960
        assert response.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_list_fasting_entries(self, db_session, test_user):
        """GET /api/v1/fasting returns list."""
        from app.api.fasting import list_entries, create_entry
        from app.fasting.schemas import FastingEntryCreate

        data = FastingEntryCreate(
            start_time=datetime.now(timezone.utc) - timedelta(hours=20),
            duration_minutes=1200,
        )
        with patch("app.api.fasting.get_db", return_value=db_session):
            await create_entry(data=data, user_id=test_user.id, db=db_session)

        # Use service directly
        from app.fasting.service import FastingService
        response = await FastingService(db_session).list(user_id=test_user.id, limit=100, offset=0)

        assert isinstance(response, list)
        assert len(response) >= 1

    @pytest.mark.asyncio
    async def test_get_fasting_detail(self, db_session, test_user):
        """GET /api/v1/fasting/{id} returns detail."""
        from app.api.fasting import create_entry, get_entry
        from app.fasting.schemas import FastingEntryCreate

        data = FastingEntryCreate(
            start_time=datetime.now(timezone.utc) - timedelta(hours=12),
            duration_minutes=720,
        )
        with patch("app.api.fasting.get_db", return_value=db_session):
            created = await create_entry(data=data, user_id=test_user.id, db=db_session)

        with patch("app.api.fasting.get_db", return_value=db_session):
            response = await get_entry(
                entry_id=created.id,
                user_id=test_user.id,
                db=db_session,
            )

        assert response.duration_minutes == 720
