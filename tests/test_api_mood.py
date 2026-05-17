"""Integration tests for the Mood API endpoints."""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone


class TestMoodAPI:
    """Tests for /api/v1/mood endpoints."""

    @pytest.mark.asyncio
    async def test_create_mood_entry(self, db_session, test_user):
        """POST /api/v1/mood creates a mood entry."""
        from app.api.mood import create_mood
        from app.mood.schemas import MoodEntryCreate

        data = MoodEntryCreate(
            score=7,
            notes="Feeling good today",
            logged_at=datetime.now(timezone.utc),
        )

        with patch("app.api.mood.get_db", return_value=db_session):
            response = await create_mood(
                data=data,
                user_id=test_user.id,
                db=db_session,
            )

        assert response.score == 7
        assert response.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_list_mood_entries(self, db_session, test_user):
        """List mood entries via service."""
        from app.mood.service import MoodService
        from app.mood.schemas import MoodEntryCreate

        data = MoodEntryCreate(
            score=5,
            logged_at=datetime.now(timezone.utc),
        )
        await MoodService(db_session).create_entry(test_user.id, data)

        response = await MoodService(db_session).list_entries(test_user.id)
        assert isinstance(response, list)
        assert len(response) >= 1

    @pytest.mark.asyncio
    async def test_delete_mood_entry(self, db_session, test_user):
        """Delete mood entry via service."""
        from app.mood.service import MoodService
        from app.mood.schemas import MoodEntryCreate

        data = MoodEntryCreate(
            score=3,
            logged_at=datetime.now(timezone.utc),
        )
        created = await MoodService(db_session).create_entry(test_user.id, data)

        deleted = await MoodService(db_session).delete_entry(test_user.id, created.id)
        assert deleted is True
