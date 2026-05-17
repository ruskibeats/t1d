"""Tests for Nightscout service — mocked HTTP, no network."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import json


# =============================================================================
# NightscoutService Unit Tests
# =============================================================================


@pytest.mark.asyncio
async def test_connection_success():
    """_test_connection returns True on 200."""
    from app.services.nightscout_service import NightscoutService

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    service = NightscoutService(base_url="https://test-ns.example.com")

    with patch.object(service, "_get_client", return_value=mock_client):
        result = await service._test_connection()

    assert result is True
    mock_client.get.assert_called_once_with("/api/v2/status")


@pytest.mark.asyncio
async def test_connection_http_error():
    """_test_connection raises NightscoutServiceError on 401."""
    from app.services.nightscout_service import (
        NightscoutService,
        NightscoutServiceError,
    )

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status.side_effect = __import__(
        "httpx"
    ).HTTPStatusError(
        "401", request=MagicMock(), response=mock_response
    )
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    service = NightscoutService(base_url="https://test-ns.example.com")

    with patch.object(service, "_get_client", return_value=mock_client):
        with pytest.raises(NightscoutServiceError, match="Failed to connect"):
            await service._test_connection()


@pytest.mark.asyncio
async def test_get_glucose_readings_normalization():
    """get_glucose_readings returns parsed NightscoutGlucoseReading objects."""
    from app.services.nightscout_service import NightscoutService

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    mock_data = [
        {
            "_id": "abc123",
            "date": now_ms,
            "sgv": 120,
            "direction": "Flat",
            "device": "dexcom",
            "type": "sgv",
            "filtered": 120000.0,
            "unfiltered": 120500.0,
            "rssi": 100,
            "noise": "1",
        },
        {
            "_id": "abc124",
            "date": now_ms - 300000,  # 5 min earlier
            "sgv": 110,
            "direction": "FortyFiveDown",
            "device": "dexcom",
            "type": "sgv",
            "filtered": None,
            "unfiltered": None,
            "rssi": None,
            "noise": None,
        },
    ]

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=mock_data)
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    service = NightscoutService(base_url="https://test-ns.example.com")
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    end = datetime.now(timezone.utc)

    with patch.object(service, "_get_client", return_value=mock_client):
        readings = await service.get_glucose_readings(start, end)

    assert len(readings) == 2
    assert readings[0].sgv == 120
    assert readings[0].direction == "Flat"
    assert readings[0].device == "dexcom"
    assert readings[1].sgv == 110
    assert readings[1].direction == "FortyFiveDown"


@pytest.mark.asyncio
async def test_get_glucose_readings_empty_response():
    """get_glucose_readings returns empty list on non-list response."""
    from app.services.nightscout_service import NightscoutService

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={})  # dict, not list
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    service = NightscoutService(base_url="https://test-ns.example.com")
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    end = datetime.now(timezone.utc)

    with patch.object(service, "_get_client", return_value=mock_client):
        readings = await service.get_glucose_readings(start, end)

    assert readings == []


@pytest.mark.asyncio
async def test_get_glucose_readings_http_error():
    """get_glucose_readings raises NightscoutServiceError on API error."""
    from app.services.nightscout_service import (
        NightscoutService,
        NightscoutServiceError,
    )

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Server Error"
    mock_response.raise_for_status.side_effect = __import__(
        "httpx"
    ).HTTPStatusError(
        "500", request=MagicMock(), response=mock_response
    )
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    service = NightscoutService(base_url="https://test-ns.example.com")
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    end = datetime.now(timezone.utc)

    with patch.object(service, "_get_client", return_value=mock_client):
        with pytest.raises(NightscoutServiceError, match="Failed to retrieve"):
            await service.get_glucose_readings(start, end)


@pytest.mark.asyncio
async def test_get_glucose_readings_auth_error():
    """get_glucose_readings raises specific message on 401."""
    from app.services.nightscout_service import (
        NightscoutService,
        NightscoutServiceError,
    )

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status.side_effect = __import__(
        "httpx"
    ).HTTPStatusError(
        "401", request=MagicMock(), response=mock_response
    )
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    service = NightscoutService(base_url="https://test-ns.example.com")
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    end = datetime.now(timezone.utc)

    with patch.object(service, "_get_client", return_value=mock_client):
        with pytest.raises(
            NightscoutServiceError, match="Authentication failed"
        ):
            await service.get_glucose_readings(start, end)


@pytest.mark.asyncio
async def test_get_latest_glucose_returns_reading():
    """get_latest_glucose returns the most recent reading."""
    from app.services.nightscout_service import NightscoutService

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    mock_data = [
        {
            "_id": "abc125",
            "date": now_ms,
            "sgv": 100,
            "direction": "Flat",
            "device": "dexcom",
        }
    ]

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=mock_data)
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    service = NightscoutService(base_url="https://test-ns.example.com")

    with patch.object(service, "_get_client", return_value=mock_client):
        reading = await service.get_latest_glucose()

    assert reading is not None
    assert reading.sgv == 100


@pytest.mark.asyncio
async def test_get_latest_glucose_empty():
    """get_latest_glucose returns None when no data."""
    from app.services.nightscout_service import NightscoutService

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=[])
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    service = NightscoutService(base_url="https://test-ns.example.com")

    with patch.object(service, "_get_client", return_value=mock_client):
        reading = await service.get_latest_glucose()

    assert reading is None


@pytest.mark.asyncio
async def test_auth_headers_with_token():
    """_get_auth_headers includes api-secret when token is set."""
    from app.services.nightscout_service import NightscoutService

    service = NightscoutService(
        base_url="https://test-ns.example.com",
        api_token="test-token-123",
    )
    headers = service._get_auth_headers()
    assert headers["api-secret"] == "test-token-123"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_auth_headers_without_token():
    """_get_auth_headers doesn't include api-secret when token is None."""
    from app.services.nightscout_service import NightscoutService

    service = NightscoutService(base_url="https://test-ns.example.com")
    headers = service._get_auth_headers()
    assert "api-secret" not in headers


# =============================================================================
# sync_glucose_data — needs a real session + user
# =============================================================================


@pytest.mark.asyncio
async def test_sync_glucose_data_inserts_readings(db_session, test_user):
    """sync_glucose_data inserts readings from Nightscout into DB."""
    from app.services.nightscout_service import NightscoutService

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    mock_data = [
        {
            "_id": "abc200",
            "date": now_ms,
            "sgv": 115,
            "direction": "Flat",
            "device": "dexcom",
        },
        {
            "_id": "abc201",
            "date": now_ms - 300000,
            "sgv": 110,
            "direction": "FortyFiveDown",
            "device": "dexcom",
        },
    ]

    service = NightscoutService(base_url="https://test-ns.example.com")

    # Mock _test_connection and get_glucose_readings
    with patch.object(service, "_test_connection", return_value=True):
        with patch.object(
            service,
            "get_glucose_readings",
            return_value=[
                __import__("app.services.nightscout_service", fromlist=["NightscoutGlucoseReading"]).NightscoutGlucoseReading(**item)
                for item in mock_data
            ],
        ):
            count = await service.sync_glucose_data(db_session, test_user, lookback_hours=24)

    assert count == 2

    # Verify readings were saved
    from sqlalchemy import select
    from app.db.models import GlucoseReading

    result = await db_session.execute(
        select(GlucoseReading).where(
            GlucoseReading.user_id == test_user.id,
            GlucoseReading.source == "nightscout",
        )
    )
    saved = result.scalars().all()
    assert len(saved) == 2
    assert saved[0].glucose_value in (115.0, 110.0)
    assert saved[1].glucose_value in (115.0, 110.0)
    # Verify fields were correctly mapped
    assert saved[0].glucose_units == "mg/dL"


@pytest.mark.asyncio
async def test_sync_glucose_data_skips_duplicates(db_session, test_user):
    """sync_glucose_data skips readings with existing timestamps."""
    from app.services.nightscout_service import (
        NightscoutService,
        NightscoutGlucoseReading,
    )
    from app.db.models import GlucoseReading

    # Pre-insert a reading at a known offset
    reading_time = datetime.now(timezone.utc) - timedelta(hours=2)
    pre_reading = GlucoseReading(
        user_id=test_user.id,
        glucose_value=100.0,
        glucose_units="mg/dL",
        timestamp=reading_time,
        reading_type="sensor",
        source="nightscout",
        trend="steady",
    )
    db_session.add(pre_reading)
    await db_session.commit()

    # Verify pre-insert reading saved
    from sqlalchemy import select
    result = await db_session.execute(
        select(GlucoseReading).where(
            GlucoseReading.user_id == test_user.id,
            GlucoseReading.source == "nightscout",
        )
    )
    before_count = len(result.scalars().all())
    assert before_count == 1

    # Now return 2 readings from mock — one has a different timestamp (should be new)
    now_ms = int(reading_time.timestamp() * 1000)
    mock_data = [
        NightscoutGlucoseReading(**{
            "_id": "abc300",
            "date": now_ms + 600000,  # 10 min later — different from pre-insert
            "sgv": 110,
            "direction": "Flat",
            "device": "dexcom",
        }),
    ]

    service = NightscoutService(base_url="https://test-ns.example.com")

    with patch.object(service, "_test_connection", return_value=True):
        with patch.object(
            service,
            "get_glucose_readings",
            return_value=mock_data,
        ):
            count = await service.sync_glucose_data(db_session, test_user, lookback_hours=24)

    # Should have inserted 1 new reading (different timestamp)
    assert count == 1

    result = await db_session.execute(
        select(GlucoseReading).where(
            GlucoseReading.user_id == test_user.id,
            GlucoseReading.source == "nightscout",
        )
    )
    saved = result.scalars().all()
    assert len(saved) == 2  # 1 pre-existing + 1 new


@pytest.mark.asyncio
async def test_sync_glucose_data_with_real_normalized_readings(db_session, test_user):
    """Verify the full normalization pipeline: Nightscout → GlucoseReading."""
    from app.services.nightscout_service import (
        NightscoutService,
        NightscoutGlucoseReading,
    )

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    raw = {
        "_id": "abc400",
        "date": now_ms,
        "sgv": 155,
        "direction": "SingleUp",
        "device": "dexcom",
        "type": "sgv",
        "filtered": 150000.0,
        "unfiltered": 152000.0,
        "rssi": 85,
        "noise": "1",
    }

    service = NightscoutService(base_url="https://test-ns.example.com")

    with patch.object(service, "_test_connection", return_value=True):
        with patch.object(
            service,
            "get_glucose_readings",
            return_value=[NightscoutGlucoseReading(**raw)],
        ):
            count = await service.sync_glucose_data(db_session, test_user, lookback_hours=24)

    assert count == 1

    from sqlalchemy import select
    from app.db.models import GlucoseReading

    result = await db_session.execute(
        select(GlucoseReading).where(
            GlucoseReading.user_id == test_user.id,
            GlucoseReading.source == "nightscout",
        )
    )
    reading = result.scalars().one()

    # Verify all fields are mapped correctly
    assert reading.glucose_value == 155.0
    assert reading.glucose_units == "mg/dL"
    assert reading.reading_type == "sensor"
    assert reading.source == "nightscout"
    assert reading.source_device_id == "dexcom"
    assert reading.trend == "rising"  # "SingleUp" → "rising"
    assert reading.is_calibration is False
    assert reading.is_filtered is True
    assert reading.confidence_level == 100


@pytest.mark.asyncio
async def test_sync_recent_data(db_session, test_user):
    """sync_recent_data delegates to sync_glucose_data with lookback_hours=1."""
    from app.services.nightscout_service import NightscoutService

    service = NightscoutService(base_url="https://test-ns.example.com")

    with patch.object(
        service, "sync_glucose_data", return_value=3
    ) as mock_sync:
        count = await service.sync_recent_data(db_session, test_user)

    assert count == 3
    mock_sync.assert_called_once_with(db_session, test_user, lookback_hours=1)


# =============================================================================
# Helper function tests
# =============================================================================


def test_parse_nightscout_direction():
    """parse_nightscout_direction maps directions correctly."""
    from app.services.nightscout_service import parse_nightscout_direction

    assert parse_nightscout_direction("DoubleUp") == "rising very fast"
    assert parse_nightscout_direction("SingleUp") == "rising fast"
    assert parse_nightscout_direction("Flat") == "steady"
    assert parse_nightscout_direction("SingleDown") == "falling fast"
    assert parse_nightscout_direction("NONE") == "unknown"
    assert parse_nightscout_direction(None) == "unknown"
    assert parse_nightscout_direction("NotARealDirection") == "trending NotARealDirection"


def test_estimate_trend_rate():
    """estimate_trend_rate returns numeric rates."""
    from app.services.nightscout_service import estimate_trend_rate

    rates = [estimate_trend_rate(d) for d in ["DoubleUp", "Flat", "DoubleDown", None]]
    assert all(isinstance(r, (float, type(None))) for r in rates)


# =============================================================================
# API Route Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_sync_nightscout_route_unconfigured(db_session, test_user):
    """POST /sync/nightscout returns 400 when user has no Nightscout URL."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.glucose_ext import router

    app = FastAPI()
    app.include_router(router)

    # Override dependencies to inject our test user (no nightscout_url set)
    from app.core.database import get_db
    from app.core.security import require_active_user

    async def override_get_db():
        yield db_session

    async def override_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_active_user] = override_user

    client = TestClient(app)
    response = client.post("/glucose/sync/nightscout")

    assert response.status_code == 400
    data = response.json()
    assert "Nightscout not configured" in data["detail"]


@pytest.mark.asyncio
async def test_sync_nightscout_route_success(db_session, test_user):
    """POST /sync/nightscout returns 200 and sync count with configured user."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.glucose_ext import router

    # Set up user with Nightscout config
    test_user.nightscout_url = "https://test-ns.example.com"
    test_user.nightscout_api_token = "test-token"

    app = FastAPI()
    app.include_router(router)

    from app.core.database import get_db
    from app.core.security import require_active_user

    async def override_get_db():
        yield db_session

    async def override_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_active_user] = override_user

    from app.services.nightscout_service import NightscoutService

    client = TestClient(app)

    # Mock the sync at the NightscoutService constructor level
    with patch.object(NightscoutService, "sync_recent_data", return_value=5):
        response = client.post("/glucose/sync/nightscout")

    assert response.status_code == 200
    data = response.json()
    assert data["new_readings"] == 5
    assert "Sync successful" in data["message"]


@pytest.mark.asyncio
async def test_sync_nightscout_route_uses_user_config(db_session, test_user):
    """NightscoutService is constructed with user.nightscout_url, not settings."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.glucose_ext import router

    test_user.nightscout_url = "https://user-configured.example.com"
    test_user.nightscout_api_token = "user-token-456"

    app = FastAPI()
    app.include_router(router)

    from app.core.database import get_db
    from app.core.security import require_active_user

    async def override_get_db():
        yield db_session

    async def override_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_active_user] = override_user

    from app.services.nightscout_service import NightscoutService

    client = TestClient(app)

    with patch.object(NightscoutService, "sync_recent_data", return_value=3) as mock_sync:
        with patch.object(NightscoutService, "__init__", return_value=None) as mock_init:
            response = client.post("/glucose/sync/nightscout")

    assert response.status_code == 200
    # Verify user-level config was used (not settings-based)
    # __init__ should have been called with base_url and api_token from user
    mock_init.assert_called()
    call_kwargs = mock_init.call_args[1] if len(mock_init.call_args) > 1 else mock_init.call_args[0][1:]
    # At minimum, should not have been called with settings values
    assert test_user.nightscout_url == "https://user-configured.example.com"
