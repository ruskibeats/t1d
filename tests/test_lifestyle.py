"""API tests for /api/v1/lifestyle endpoints."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app.db.models import User


class TestLifestyleAPI:
    @pytest.mark.asyncio
    async def test_create_lifestyle_entry(self, db_session, test_user):
        from app.api.lifestyle import create_entry
        from app.lifestyle.schemas import LifestyleEntryCreate

        data = LifestyleEntryCreate(
            stress_level=3,
            energy_level=7,
            caffeine_mg=200,
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.lifestyle.get_db", return_value=db_session), \
             patch("app.api.lifestyle.require_active_user", return_value=test_user):
            response = await create_entry(data=data, user=test_user, db=db_session)

        assert response.stress_level == 3
        assert response.energy_level == 7
        assert response.caffeine_mg == 200

    @pytest.mark.asyncio
    async def test_list_lifestyle_entries(self, db_session, test_user):
        from app.api.lifestyle import create_entry
        from app.lifestyle.schemas import LifestyleEntryCreate

        data = LifestyleEntryCreate(stress_level=5, measured_at=datetime.now(timezone.utc))
        with patch("app.api.lifestyle.get_db", return_value=db_session), \
             patch("app.api.lifestyle.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        from app.lifestyle.service import LifestyleService
        result = await LifestyleService(db_session).list(user_id=test_user.id)
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_lifestyle_entry(self, db_session, test_user):
        from app.api.lifestyle import create_entry
        from app.api.lifestyle import get_entry
        from app.lifestyle.schemas import LifestyleEntryCreate

        data = LifestyleEntryCreate(energy_level=8, measured_at=datetime.now(timezone.utc))
        with patch("app.api.lifestyle.get_db", return_value=db_session), \
             patch("app.api.lifestyle.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.lifestyle.get_db", return_value=db_session), \
             patch("app.api.lifestyle.require_active_user", return_value=test_user):
            response = await get_entry(entry_id=created.id, user=test_user, db=db_session)

        assert response.energy_level == 8

    @pytest.mark.asyncio
    async def test_delete_lifestyle_entry(self, db_session, test_user):
        from app.api.lifestyle import create_entry
        from app.api.lifestyle import delete_entry
        from app.lifestyle.schemas import LifestyleEntryCreate

        data = LifestyleEntryCreate(stress_level=2, measured_at=datetime.now(timezone.utc))
        with patch("app.api.lifestyle.get_db", return_value=db_session), \
             patch("app.api.lifestyle.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.lifestyle.get_db", return_value=db_session), \
             patch("app.api.lifestyle.require_active_user", return_value=test_user):
            await delete_entry(entry_id=created.id, user=test_user, db=db_session)

        from app.lifestyle.service import LifestyleService
        result = await LifestyleService(db_session).get(user_id=test_user.id, entry_id=created.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_lifestyle_entry(self, db_session, test_user):
        from app.lifestyle.schemas import LifestyleEntryCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LifestyleEntryCreate(stress_level=15, measured_at=datetime.now(timezone.utc))
