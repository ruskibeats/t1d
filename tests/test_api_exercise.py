"""Integration tests for the Exercise API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from app.db.models import User


class TestExerciseAPI:
    """Tests for /api/v1/exercise endpoints."""

    @pytest.mark.asyncio
    async def test_create_exercise_entry(self, db_session, test_user):
        """POST /api/v1/exercise creates an exercise entry."""
        from app.api.exercise import create_entry
        from app.exercise.schemas import ExerciseEntryCreate

        data = ExerciseEntryCreate(
            type="running",
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc),
            duration_minutes=60,
            calories=500,
            heart_rate_avg=150,
        )

        with patch("app.api.exercise.get_db", return_value=db_session), \
             patch("app.api.exercise.require_active_user", return_value=test_user):
            response = await create_entry(
                data=data,
                user=test_user,
                db=db_session,
            )

        assert response.type == "running"
        assert response.duration_minutes == 60
        assert response.calories == 500

    @pytest.mark.asyncio
    async def test_list_exercise_entries(self, db_session, test_user):
        """GET /api/v1/exercise returns list of entries."""
        from app.api.exercise import create_entry
        from app.exercise.schemas import ExerciseEntryCreate

        data = ExerciseEntryCreate(
            type="cycling",
            start_time=datetime.now(timezone.utc),
            duration_minutes=30,
        )
        with patch("app.api.exercise.get_db", return_value=db_session), \
             patch("app.api.exercise.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        from app.exercise.service import ExerciseService
        response = await ExerciseService(db_session).list_entries(user_id=test_user.id)
        assert isinstance(response, list)

    @pytest.mark.asyncio
    async def test_get_exercise_detail(self, db_session, test_user):
        """GET /api/v1/exercise/{id} returns entry detail."""
        from app.api.exercise import create_entry, get_entry
        from app.exercise.schemas import ExerciseEntryCreate

        data = ExerciseEntryCreate(
            type="swimming",
            start_time=datetime.now(timezone.utc),
            duration_minutes=45,
        )
        with patch("app.api.exercise.get_db", return_value=db_session), \
             patch("app.api.exercise.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.exercise.get_db", return_value=db_session), \
             patch("app.api.exercise.require_active_user", return_value=test_user):
            response = await get_entry(
                entry_id=created.id,
                user=test_user,
                db=db_session,
            )

        assert response.type == "swimming"
        assert response.duration_minutes == 45
