"""API tests for /api/v1/body-composition endpoints."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app.db.models import User


class TestBodyCompositionAPI:
    @pytest.mark.asyncio
    async def test_create_body_composition_entry(self, db_session, test_user):
        from app.api.body_composition import create_entry
        from app.body_composition.schemas import BodyCompositionEntryCreate

        data = BodyCompositionEntryCreate(
            weight_kg=75.5,
            body_fat_percent=18.0,
            bmi=24.5,
            lean_mass_kg=62.0,
            waist_cm=85,
            measured_at=datetime.now(timezone.utc),
        )
        with patch("app.api.body_composition.get_db", return_value=db_session), \
             patch("app.api.body_composition.require_active_user", return_value=test_user):
            response = await create_entry(data=data, user=test_user, db=db_session)

        assert response.weight_kg == 75.5
        assert response.body_fat_percent == 18.0
        assert response.bmi == 24.5

    @pytest.mark.asyncio
    async def test_list_body_composition_entries(self, db_session, test_user):
        from app.api.body_composition import create_entry
        from app.body_composition.schemas import BodyCompositionEntryCreate

        data = BodyCompositionEntryCreate(weight_kg=76, measured_at=datetime.now(timezone.utc))
        with patch("app.api.body_composition.get_db", return_value=db_session), \
             patch("app.api.body_composition.require_active_user", return_value=test_user):
            await create_entry(data=data, user=test_user, db=db_session)

        from app.body_composition.service import BodyCompositionService
        result = await BodyCompositionService(db_session).list(user_id=test_user.id)
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_body_composition_entry(self, db_session, test_user):
        from app.api.body_composition import create_entry
        from app.api.body_composition import get_entry
        from app.body_composition.schemas import BodyCompositionEntryCreate

        data = BodyCompositionEntryCreate(weight_kg=74, measured_at=datetime.now(timezone.utc))
        with patch("app.api.body_composition.get_db", return_value=db_session), \
             patch("app.api.body_composition.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.body_composition.get_db", return_value=db_session), \
             patch("app.api.body_composition.require_active_user", return_value=test_user):
            response = await get_entry(entry_id=created.id, user=test_user, db=db_session)

        assert response.weight_kg == 74

    @pytest.mark.asyncio
    async def test_delete_body_composition_entry(self, db_session, test_user):
        from app.api.body_composition import create_entry
        from app.api.body_composition import delete_entry
        from app.body_composition.schemas import BodyCompositionEntryCreate

        data = BodyCompositionEntryCreate(weight_kg=73, measured_at=datetime.now(timezone.utc))
        with patch("app.api.body_composition.get_db", return_value=db_session), \
             patch("app.api.body_composition.require_active_user", return_value=test_user):
            created = await create_entry(data=data, user=test_user, db=db_session)

        with patch("app.api.body_composition.get_db", return_value=db_session), \
             patch("app.api.body_composition.require_active_user", return_value=test_user):
            await delete_entry(entry_id=created.id, user=test_user, db=db_session)

        from app.body_composition.service import BodyCompositionService
        result = await BodyCompositionService(db_session).get(user_id=test_user.id, entry_id=created.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_body_composition_entry(self, db_session, test_user):
        from app.body_composition.schemas import BodyCompositionEntryCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BodyCompositionEntryCreate(weight_kg=-5, measured_at=datetime.now(timezone.utc))
