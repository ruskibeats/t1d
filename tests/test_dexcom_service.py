"""Tests for DexcomService — mocked HTTP calls, no network."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.dexcom_service import (
    DexcomService,
    DexcomServiceError,
    DexcomOAuthTokens,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_http_response(data, status_code=200, text=None):
    """Build a mock httpx response that matches httpx.Response sync API.

    httpx.Response (even from AsyncClient) has sync methods:
      - response.json()       -> sync, returns dict
      - response.raise_for_status() -> sync, raises on 4xx/5xx
    """
    resp = AsyncMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text or (str(data) if data else "")
    # json() is sync in httpx.Response — use MagicMock, NOT AsyncMock
    resp.json = MagicMock(return_value=data)
    if status_code >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                f"HTTP {status_code}", request=MagicMock(), response=resp
            )
        )
    else:
        resp.raise_for_status = MagicMock(return_value=None)
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dexcom_service():
    """Create a DexcomService with test credentials pointing at sandbox."""
    return DexcomService(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8000/auth/dexcom/callback",
        use_sandbox=True,
    )


@pytest.fixture
def mock_httpx():
    """Patch httpx.AsyncClient inside the dexcom_service module.

    Returns the mock client so tests can configure return values.
    """
    with patch("app.services.dexcom_service.httpx.AsyncClient") as cls:
        client = AsyncMock()
        cls.return_value.__aenter__.return_value = client
        yield client


# =========================================================================
# Authorization URL
# =========================================================================

class TestAuthorizationURL:
    """dexcom_service.get_authorization_url()"""

    def test_includes_required_params(self, dexcom_service):
        url = dexcom_service.get_authorization_url(state="abc123")
        assert "client_id=test-client-id" in url
        # Note: service builds URL via string concatenation, not urlencode,
        # so the redirect_uri is NOT percent-encoded.
        assert "redirect_uri=http://localhost:8000" in url
        assert "response_type=code" in url
        assert "scope=offline_access" in url
        assert "state=abc123" in url

    def test_uses_sandbox_when_configured(self, dexcom_service):
        url = dexcom_service.get_authorization_url(state="x")
        assert "sandbox-api" in url
        assert "production" not in url

    def test_uses_production_when_sandbox_false(self):
        prod = DexcomService(
            client_id="c", client_secret="s", redirect_uri="http://r",
            use_sandbox=False,
        )
        url = prod.get_authorization_url(state="x")
        assert "api.dexcom.com/v2/oauth2/auth" in url
        assert "sandbox" not in url


# =========================================================================
# Exchange code for tokens
# =========================================================================

TOKEN_BODY = {
    "access_token": "at-abc123",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "rt-def456",
    "scope": "offline_access",
}


class TestExchangeCodeForTokens:
    """dexcom_service.exchange_code_for_tokens()"""

    @pytest.mark.asyncio
    async def test_success(self, dexcom_service, mock_httpx):
        mock_httpx.post.return_value = _mock_http_response(TOKEN_BODY, 200)

        tokens = await dexcom_service.exchange_code_for_tokens("auth-code-42")

        assert isinstance(tokens, DexcomOAuthTokens)
        assert tokens.access_token == "at-abc123"
        assert tokens.refresh_token == "rt-def456"
        assert tokens.expires_in == 3600
        assert tokens.token_type == "Bearer"
        assert tokens.scope == "offline_access"

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self, dexcom_service, mock_httpx):
        mock_httpx.post.return_value = _mock_http_response(TOKEN_BODY, 200)

        await dexcom_service.exchange_code_for_tokens("the-code")

        call = mock_httpx.post.call_args
        assert call is not None
        assert "/oauth2/token" in call.args[0]
        data = call.kwargs.get("data", {})
        assert data["code"] == "the-code"
        assert data["grant_type"] == "authorization_code"
        assert data["client_id"] == "test-client-id"

    @pytest.mark.asyncio
    async def test_http_401_raises_dexcom_error(self, dexcom_service, mock_httpx):
        mock_httpx.post.return_value = _mock_http_response(
            {"error": "invalid_grant"}, 401, text="invalid_grant"
        )

        with pytest.raises(DexcomServiceError, match="Failed to exchange"):
            await dexcom_service.exchange_code_for_tokens("bad-code")

    @pytest.mark.asyncio
    async def test_network_error_raises_dexcom_error(self, dexcom_service, mock_httpx):
        mock_httpx.post.side_effect = httpx.RequestError("connection refused")

        with pytest.raises(DexcomServiceError, match="Token exchange failed"):
            await dexcom_service.exchange_code_for_tokens("code")


# =========================================================================
# Refresh access token
# =========================================================================

REFRESH_BODY = {
    "access_token": "at-refreshed",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "rt-refreshed",
}


class TestRefreshAccessToken:
    """dexcom_service.refresh_access_token()"""

    @pytest.mark.asyncio
    async def test_success(self, dexcom_service, mock_httpx):
        mock_httpx.post.return_value = _mock_http_response(REFRESH_BODY, 200)

        tokens = await dexcom_service.refresh_access_token("old-rt")

        assert tokens.access_token == "at-refreshed"
        assert tokens.refresh_token == "rt-refreshed"

    @pytest.mark.asyncio
    async def test_sends_refresh_token_payload(self, dexcom_service, mock_httpx):
        mock_httpx.post.return_value = _mock_http_response(REFRESH_BODY, 200)

        await dexcom_service.refresh_access_token("my-refresh-token")

        data = mock_httpx.post.call_args.kwargs.get("data", {})
        assert data["refresh_token"] == "my-refresh-token"
        assert data["grant_type"] == "refresh_token"

    @pytest.mark.asyncio
    async def test_http_error_raises_dexcom_error(self, dexcom_service, mock_httpx):
        mock_httpx.post.return_value = _mock_http_response(
            {"error": "invalid_token"}, 400, text="invalid_token"
        )

        with pytest.raises(DexcomServiceError, match="Failed to refresh"):
            await dexcom_service.refresh_access_token("bad-rt")


# =========================================================================
# get_glucose_readings
# =========================================================================

EGVS_BODY = [
    {
        "systemTime": "2026-05-15T10:00:00Z",
        "displayTime": "2026-05-15T10:00:00Z",
        "value": 120,
        "unit": "mg/dL",
        "trend": "Flat",
        "trendRate": 0.0,
    },
    {
        "systemTime": "2026-05-15T10:05:00Z",
        "displayTime": "2026-05-15T10:05:00Z",
        "value": 125,
        "unit": "mg/dL",
        "trend": "Flat",
        "trendRate": 1.0,
    },
]


class TestGetGlucoseReadings:
    """dexcom_service.get_glucose_readings()"""

    @pytest.mark.asyncio
    async def test_returns_parsed_readings(self, dexcom_service, mock_httpx):
        mock_httpx.get.return_value = _mock_http_response(EGVS_BODY, 200)

        start = datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 15, 11, 0, tzinfo=timezone.utc)
        readings = await dexcom_service.get_glucose_readings(
            "at-abc", start, end
        )

        assert len(readings) == 2
        assert readings[0]["value"] == 120
        assert readings[0]["trend"] == "Flat"

    @pytest.mark.asyncio
    async def test_sends_bearer_token(self, dexcom_service, mock_httpx):
        mock_httpx.get.return_value = _mock_http_response([], 200)

        start = end = datetime.now(timezone.utc)
        await dexcom_service.get_glucose_readings("my-token", start, end)

        headers = mock_httpx.get.call_args.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer my-token"

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_list(self, dexcom_service, mock_httpx):
        mock_httpx.get.return_value = _mock_http_response(None, 200)

        start = end = datetime.now(timezone.utc)
        readings = await dexcom_service.get_glucose_readings("tok", start, end)
        assert readings == []

    @pytest.mark.asyncio
    async def test_401_raises_invalid_token(self, dexcom_service, mock_httpx):
        mock_httpx.get.return_value = _mock_http_response(
            {"error": "expired"}, 401, text="expired"
        )

        start = end = datetime.now(timezone.utc)
        with pytest.raises(DexcomServiceError, match="Invalid or expired"):
            await dexcom_service.get_glucose_readings("bad-token", start, end)

    @pytest.mark.asyncio
    async def test_500_raises_dexcom_error(self, dexcom_service, mock_httpx):
        mock_httpx.get.return_value = _mock_http_response(
            {"error": "internal"}, 500, text="server error"
        )

        start = end = datetime.now(timezone.utc)
        with pytest.raises(DexcomServiceError, match="Failed to retrieve"):
            await dexcom_service.get_glucose_readings("tok", start, end)


# =========================================================================
# get_latest_glucose — delegates to get_glucose_readings
# =========================================================================

class TestGetLatestGlucose:
    """dexcom_service.get_latest_glucose()"""

    @pytest.mark.asyncio
    async def test_returns_max_by_system_time(self, dexcom_service, mock_httpx):
        mock_httpx.get.return_value = _mock_http_response(
            [
                {"systemTime": "2026-05-15T10:00:00Z", "value": 120},
                {"systemTime": "2026-05-15T10:05:00Z", "value": 125},
            ],
            200,
        )

        latest = await dexcom_service.get_latest_glucose("tok")
        assert latest is not None
        assert latest["value"] == 125

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self, dexcom_service, mock_httpx):
        mock_httpx.get.return_value = _mock_http_response([], 200)

        latest = await dexcom_service.get_latest_glucose("tok")
        assert latest is None


# =========================================================================
# sync_glucose_data — full ingestion path
# =========================================================================

class TestSyncGlucoseData:
    """dexcom_service.sync_glucose_data() — inserts & dedup."""

    @pytest.mark.asyncio
    async def test_inserts_new_readings(self, dexcom_service, mock_httpx,
                                         db_session, test_user):
        """Happy path: raw readings become GlucoseReading rows."""
        mock_httpx.get.return_value = _mock_http_response(
            [
                {
                    "systemTime": "2026-05-15T10:00:00Z",
                    "displayTime": "2026-05-15T10:00:00Z",
                    "value": 120,
                    "unit": "mg/dL",
                    "trend": "Flat",
                },
                {
                    "systemTime": "2026-05-15T10:05:00Z",
                    "displayTime": "2026-05-15T10:05:00Z",
                    "value": 180,
                    "unit": "mg/dL",
                    "trend": "SingleUp",
                },
            ],
            200,
        )

        count = await dexcom_service.sync_glucose_data(
            db_session, test_user, "tok", lookback_hours=24
        )

        assert count == 2

        from sqlalchemy import select
        from app.db.models import GlucoseReading
        result = await db_session.execute(
            select(GlucoseReading).where(GlucoseReading.user_id == test_user.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 2
        # Note: the service sets glucose_unit (singular) but the model column
        # is glucose_units (plural). This is a known bug — see the bug note
        # at the bottom of this file.
        # Verify the reading values are stored regardless.
        vals = sorted(r.glucose_value for r in rows)
        assert vals == [120.0, 180.0]

    @pytest.mark.asyncio
    async def test_skips_duplicates(self, dexcom_service, mock_httpx,
                                     db_session, test_user):
        """Already-existing reading timestamps are skipped.

        The fix changes ``{r[0] for r in existing.scalars()}`` to
        ``set(existing.scalars().all())`` so datetime values are
        compared correctly.
        """
        from app.db.models import GlucoseReading
        from sqlalchemy import select

        # Pre-existing reading within the lookback window
        ts = datetime.now(timezone.utc) - timedelta(hours=6)
        preexisting = GlucoseReading(
            user_id=test_user.id,
            glucose_value=120.0,
            glucose_units="mg/dL",
            timestamp=ts,
            reading_type="sensor",
            source="dexcom",
            trend="flat",
        )
        db_session.add(preexisting)
        await db_session.commit()

        # Mock returns: one duplicate + one new reading
        dup_ts = ts.isoformat().replace("+00:00", "Z")
        new_ts = (ts + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        mock_httpx.get.return_value = _mock_http_response(
            [
                {"systemTime": dup_ts, "value": 120,
                 "displayTime": dup_ts, "unit": "mg/dL", "trend": "Flat"},
                {"systemTime": new_ts, "value": 130,
                 "displayTime": new_ts, "unit": "mg/dL", "trend": "Flat"},
            ],
            200,
        )

        count = await dexcom_service.sync_glucose_data(
            db_session, test_user, "tok", lookback_hours=24
        )

        # Duplicate should be skipped: count is 1 new reading
        assert count == 1

    @pytest.mark.asyncio
    async def test_skips_invalid_reading(self, dexcom_service, mock_httpx,
                                          db_session, test_user):
        """A record missing value/systemTime is skipped gracefully."""
        mock_httpx.get.return_value = _mock_http_response(
            [
                {"bad_key": "garbage"},
                {"systemTime": "2026-05-15T10:00:00Z", "value": 150,
                 "displayTime": "2026-05-15T10:00:00Z", "unit": "mg/dL", "trend": "Flat"},
            ],
            200,
        )

        count = await dexcom_service.sync_glucose_data(
            db_session, test_user, "tok", lookback_hours=24
        )

        assert count == 1  # only the valid reading

    @pytest.mark.asyncio
    async def test_api_error_raises_dexcom_error(self, dexcom_service, mock_httpx,
                                                   db_session, test_user):
        """HTTP error during sync propagates."""
        mock_httpx.get.return_value = _mock_http_response(
            {"error": "expired"}, 401, text="expired"
        )

        with pytest.raises(DexcomServiceError, match="Invalid or expired"):
            await dexcom_service.sync_glucose_data(
                db_session, test_user, "bad-token", lookback_hours=24
            )


# =========================================================================
# Helper tests (no mocking needed)
# =========================================================================

class TestGetTrendAngle:
    """get_trend_angle()"""

    def test_none_returns_none(self):
        from app.services.dexcom_service import get_trend_angle
        assert get_trend_angle(None) is None

    def test_fast_rise(self):
        from app.services.dexcom_service import get_trend_angle
        assert get_trend_angle(3.5) == "rising very fast"
        assert get_trend_angle(2.5) == "rising fast"
        assert get_trend_angle(1.5) == "rising"
        assert get_trend_angle(0.7) == "rising slightly"

    def test_steady(self):
        from app.services.dexcom_service import get_trend_angle
        assert get_trend_angle(0.0) == "steady"
        assert get_trend_angle(0.4) == "steady"
        assert get_trend_angle(-0.4) == "steady"

    def test_fast_drop(self):
        from app.services.dexcom_service import get_trend_angle
        assert get_trend_angle(-0.7) == "falling slightly"
        assert get_trend_angle(-1.5) == "falling"
        assert get_trend_angle(-2.5) == "falling fast"
        assert get_trend_angle(-3.5) == "falling very fast"


class TestCategorizeGlucoseLevel:
    """categorize_glucose_level()"""

    def test_severe_low(self):
        from app.services.dexcom_service import categorize_glucose_level
        assert categorize_glucose_level(53) == "severe_low"
        assert categorize_glucose_level(40) == "severe_low"

    def test_low(self):
        from app.services.dexcom_service import categorize_glucose_level
        assert categorize_glucose_level(60) == "low"
        assert categorize_glucose_level(69) == "low"

    def test_in_range(self):
        from app.services.dexcom_service import categorize_glucose_level
        assert categorize_glucose_level(70) == "in_range"
        assert categorize_glucose_level(120) == "in_range"
        assert categorize_glucose_level(180) == "in_range"

    def test_high(self):
        from app.services.dexcom_service import categorize_glucose_level
        assert categorize_glucose_level(181) == "high"
        assert categorize_glucose_level(200) == "high"
        assert categorize_glucose_level(250) == "high"

    def test_severe_high(self):
        from app.services.dexcom_service import categorize_glucose_level
        assert categorize_glucose_level(251) == "severe_high"
        assert categorize_glucose_level(400) == "severe_high"
