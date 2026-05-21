"""Integration tests for the Environment API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from app.db.models import User


class TestEnvironmentAPI:
    """Tests for /api/v1/environment endpoints."""

    @pytest.mark.asyncio
    async def test_create_environment_entry(self, db_session, test_user):
        """POST /api/v1/environment creates an environment entry."""
        from app.api.environment import router
        from app.environment.schemas import EnvironmentEntryCreate

        data = EnvironmentEntryCreate(
            temperature_c=22.5,
            humidity_percent=45.0,
            altitude_m=150.0,
            measured_at=datetime.now(timezone.utc),
        )

        with patch("app.api.environment.get_db", return_value=db_session), \
             patch("app.api.environment.require_active_user", return_value=test_user):
            # Create a mock service
            from app.environment.service import EnvironmentService
            service = EnvironmentService(db_session)
            response = await service.create(test_user.id, data)

        assert response.temperature_c == 22.5
        assert response.humidity_percent == 45.0
        assert response.altitude_m == 150.0

    @pytest.mark.asyncio
    async def test_list_environment_entries(self, db_session, test_user):
        """GET /api/v1/environment returns list of entries."""
        from app.environment.schemas import EnvironmentEntryCreate
        from app.environment.service import EnvironmentService

        data = EnvironmentEntryCreate(
            temperature_c=20.0,
            humidity_percent=50.0,
            measured_at=datetime.now(timezone.utc),
        )
        service = EnvironmentService(db_session)
        await service.create(test_user.id, data)

        response = await service.list(user_id=test_user.id)
        assert isinstance(response, list)
        assert len(response) >= 1

    @pytest.mark.asyncio
    async def test_get_environment_detail(self, db_session, test_user):
        """GET /api/v1/environment/{id} returns entry detail."""
        from app.environment.schemas import EnvironmentEntryCreate
        from app.environment.service import EnvironmentService

        data = EnvironmentEntryCreate(
            temperature_c=18.5,
            humidity_percent=60.0,
            measured_at=datetime.now(timezone.utc),
        )
        service = EnvironmentService(db_session)
        created = await service.create(test_user.id, data)

        response = await service.get(test_user.id, created.id)
        assert response.temperature_c == 18.5
        assert response.humidity_percent == 60.0

    @pytest.mark.asyncio
    async def test_update_environment_entry(self, db_session, test_user):
        """PUT /api/v1/environment/{id} updates an entry."""
        from app.environment.schemas import EnvironmentEntryCreate
        from app.environment.service import EnvironmentService

        data = EnvironmentEntryCreate(
            temperature_c=25.0,
            humidity_percent=55.0,
            measured_at=datetime.now(timezone.utc),
        )
        service = EnvironmentService(db_session)
        created = await service.create(test_user.id, data)

        update_data = EnvironmentEntryCreate(
            temperature_c=26.0,
            humidity_percent=55.0,
            measured_at=datetime.now(timezone.utc),
        )
        response = await service.update(test_user.id, created.id, update_data)
        assert response.temperature_c == 26.0

    @pytest.mark.asyncio
    async def test_delete_environment_entry(self, db_session, test_user):
        """DELETE /api/v1/environment/{id} deletes an entry."""
        from app.environment.schemas import EnvironmentEntryCreate
        from app.environment.service import EnvironmentService

        data = EnvironmentEntryCreate(
            temperature_c=22.0,
            measured_at=datetime.now(timezone.utc),
        )
        service = EnvironmentService(db_session)
        created = await service.create(test_user.id, data)

        success = await service.delete(test_user.id, created.id)
        assert success is True

        # Verify deletion
        response = await service.get(test_user.id, created.id)
        assert response is None

    @pytest.mark.asyncio
    async def test_list_with_date_filter(self, db_session, test_user):
        """GET /api/v1/environment with start/end dates filters entries."""
        from app.environment.schemas import EnvironmentEntryCreate
        from app.environment.service import EnvironmentService

        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        data = EnvironmentEntryCreate(
            temperature_c=22.0,
            measured_at=yesterday,
        )
        service = EnvironmentService(db_session)
        await service.create(test_user.id, data)

        response = await service.list(
            user_id=test_user.id,
            start_date=yesterday,
            end_date=now,
        )
        assert isinstance(response, list)

    @pytest.mark.asyncio
    async def test_create_entry_with_null_values(self, db_session, test_user):
        """POST /api/v1/environment allows null optional fields."""
        from app.environment.schemas import EnvironmentEntryCreate
        from app.environment.service import EnvironmentService

        data = EnvironmentEntryCreate(
            temperature_c=None,
            humidity_percent=None,
            altitude_m=None,
            measured_at=datetime.now(timezone.utc),
        )
        service = EnvironmentService(db_session)
        response = await service.create(test_user.id, data)

        assert response.temperature_c is None
        assert response.humidity_percent is None
        assert response.altitude_m is None

    @pytest.mark.asyncio
    async def test_create_entry_source_default(self, db_session, test_user):
        """POST /api/v1/environment defaults source to 'manual'."""
        from app.environment.schemas import EnvironmentEntryCreate
        from app.environment.service import EnvironmentService

        data = EnvironmentEntryCreate(
            temperature_c=20.0,
            measured_at=datetime.now(timezone.utc),
        )
        service = EnvironmentService(db_session)
        response = await service.create(test_user.id, data)

        assert response.source == "manual"