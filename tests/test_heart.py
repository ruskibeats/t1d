"""Integration tests for the Heart API endpoints."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import patch

from app.main import app
from app.db.models import User
from app.heart.schemas import HeartRateEntryCreate
from app.core.database import get_db
from app.core.security import require_active_user
from app.api.heart import create_entry, list_entries, get_entry, delete_entry

@pytest_asyncio.fixture(scope="function")
async def client(db_session, test_user):
    """Return a TestClient for testing the FastAPI app."""
    async def override_get_db():
        yield db_session
    async def override_require_active_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_active_user] = override_require_active_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {} # Clean up overrides


class TestHeartRateAPI:
    """Tests for /api/v1/heart endpoints."""

    @pytest.mark.asyncio
    async def test_create_heart_rate_entry(self, client: TestClient, test_user: User):
        """POST /api/v1/heart creates a heart rate entry."""
        heart_rate_data = {
            "heart_rate_bpm": 72,
            "measured_at": datetime.now(timezone.utc).isoformat()
        }
        headers = {"Authorization": f"Bearer {test_user.id}"} # Mock auth for simplicity

        response = client.post("/api/v1/heart", json=heart_rate_data, headers=headers)

        assert response.status_code == 201
        assert response.json()["heart_rate_bpm"] == 72
        assert response.json()["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_list_heart_rate_entries(self, db_session, test_user):
        """GET /api/v1/heart returns a list of heart rate entries."""
        # Create an entry first
        heart_rate_data = HeartRateEntryCreate(
            heart_rate_bpm=80,
            measured_at=datetime.now(timezone.utc)
        )
        with patch("app.api.heart.get_db", return_value=db_session), \
             patch("app.api.heart.require_active_user", return_value=test_user):
            await create_entry(data=heart_rate_data, db=db_session, user=test_user)

        with patch("app.api.heart.get_db", return_value=db_session), \
             patch("app.api.heart.require_active_user", return_value=test_user):
            response = await list_entries(
                db=db_session, user=test_user
            )

        assert isinstance(response, list)
        assert len(response) > 0
        assert response[0].heart_rate_bpm == 80

    @pytest.mark.asyncio
    async def test_get_heart_rate_entry(self, client: TestClient, test_user: User):
        """GET /api/v1/heart/{id} returns a single heart rate entry."""
        # Create an entry first
        heart_rate_data = {
            "heart_rate_bpm": 65,
            "measured_at": datetime.now(timezone.utc).isoformat()
        }
        headers = {"Authorization": f"Bearer {test_user.id}"}
        create_response = client.post("/api/v1/heart", json=heart_rate_data, headers=headers)
        entry_id = create_response.json()["id"]

        response = client.get(f"/api/v1/heart/{entry_id}", headers=headers)

        assert response.status_code == 200
        assert response.json()["id"] == entry_id
        assert response.json()["heart_rate_bpm"] == 65

    @pytest.mark.asyncio
    async def test_delete_heart_rate_entry(self, client: TestClient, test_user: User):
        """DELETE /api/v1/heart/{id} deletes a heart rate entry."""
        # Create an entry first
        heart_rate_data = {
            "heart_rate_bpm": 70,
            "measured_at": datetime.now(timezone.utc).isoformat()
        }
        headers = {"Authorization": f"Bearer {test_user.id}"}
        create_response = client.post("/api/v1/heart", json=heart_rate_data, headers=headers)
        entry_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/heart/{entry_id}", headers=headers)

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/v1/heart/{entry_id}", headers=headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_heart_rate(self, client: TestClient, test_user: User):
        """POST /api/v1/heart with invalid heart_rate_bpm returns 422."""
        heart_rate_data = {
            "heart_rate_bpm": -50,
            "measured_at": datetime.now(timezone.utc).isoformat()
        }
        headers = {"Authorization": f"Bearer {test_user.id}"}

        response = client.post("/api/v1/heart", json=heart_rate_data, headers=headers)

        assert response.status_code == 422
        assert any("heart_rate_bpm" in error.get("loc", []) and "greater than or equal" in error.get("msg", "").lower() for error in response.json()["detail"])
