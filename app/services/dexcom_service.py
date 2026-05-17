"""Dexcom API integration service.

Handles OAuth2 authentication and glucose data retrieval from Dexcom API.
Reference: https://developer.dexcom.com/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.database import AsyncSession
from app.db.models import GlucoseReading, User


logger = logging.getLogger(__name__)


# Dexcom API endpoints
DEXCOM_PRODUCTION = "https://api.dexcom.com/v2"
DEXCOM_SANDBOX = "https://sandbox-api.dexcom.com/v2"


class DexcomOAuthTokens(BaseModel):
    """Dexcom OAuth2 token response."""
    
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: Optional[str] = None


class DexcomGlucoseReading(BaseModel):
    """Dexcom glucose reading format."""
    
    system_time: datetime = Field(..., alias="systemTime")
    display_time: datetime = Field(..., alias="displayTime")
    value: float
    unit: str
    trend: Optional[str] = None
    trend_rate: Optional[float] = None


class DexcomServiceError(Exception):
    """Raised when Dexcom API communication fails."""
    pass


class DexcomService:
    """Service for Dexcom API integration.
    
    Handles OAuth2 authentication, token refresh, and glucose data retrieval.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        use_sandbox: bool = False,
    ):
        """Initialize Dexcom service.
        
        Args:
            client_id: Dexcom OAuth2 client ID
            client_secret: Dexcom OAuth2 client secret
            redirect_uri: OAuth2 redirect URI
            use_sandbox: Use sandbox environment for testing
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = DEXCOM_SANDBOX if use_sandbox else DEXCOM_PRODUCTION
        self.logger = logging.getLogger(f"{__name__}.DexcomService")
    
    # -------------------------------------------------------------------
    # OAuth2 Authentication
    # -------------------------------------------------------------------
    
    def get_authorization_url(self, state: str) -> str:
        """Generate Dexcom OAuth2 authorization URL.
        
        Args:
            state: CSRF protection state parameter
            
        Returns:
            Full authorization URL for redirect
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "offline_access",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.base_url}/oauth2/auth?{query}"
    
    async def exchange_code_for_tokens(
        self,
        authorization_code: str,
    ) -> DexcomOAuthTokens:
        """Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Code from OAuth2 callback
            
        Returns:
            OAuth2 tokens
            
        Raises:
            DexcomServiceError: If token exchange fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/oauth2/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": authorization_code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                data = response.json()
                return DexcomOAuthTokens(**data)
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Dexcom token exchange failed: {e}")
                raise DexcomServiceError(
                    f"Failed to exchange authorization code: {e.response.text}"
                ) from e
            except Exception as e:
                self.logger.error(f"Dexcom token exchange error: {e}")
                raise DexcomServiceError(f"Token exchange failed: {str(e)}") from e
    
    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> DexcomOAuthTokens:
        """Refresh expired access token using refresh token.
        
        Args:
            refresh_token: OAuth2 refresh token
            
        Returns:
            New OAuth2 tokens
            
        Raises:
            DexcomServiceError: If token refresh fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/oauth2/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                data = response.json()
                return DexcomOAuthTokens(**data)
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Dexcom token refresh failed: {e}")
                raise DexcomServiceError(
                    f"Failed to refresh access token: {e.response.text}"
                ) from e
            except Exception as e:
                self.logger.error(f"Dexcom token refresh error: {e}")
                raise DexcomServiceError(f"Token refresh failed: {str(e)}") from e
    
    # -------------------------------------------------------------------
    # Glucose Data Retrieval
    # -------------------------------------------------------------------
    
    async def get_glucose_readings(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Retrieve glucose readings from Dexcom API.
        
        Args:
            access_token: Valid OAuth2 access token
            start_date: Start of date range (UTC)
            end_date: End of date range (UTC)
            
        Returns:
            List of glucose readings from Dexcom
            
        Raises:
            DexcomServiceError: If data retrieval fails
        """
        # Format dates for Dexcom API (ISO 8601)
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/users/self/egvs",
                    params={
                        "startDate": start_str,
                        "endDate": end_str,
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, list) else []
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Dexcom data retrieval failed: {e}")
                if e.response.status_code == 401:
                    raise DexcomServiceError("Invalid or expired access token") from e
                raise DexcomServiceError(
                    f"Failed to retrieve glucose data: {e.response.text}"
                ) from e
            except Exception as e:
                self.logger.error(f"Dexcom data retrieval error: {e}")
                raise DexcomServiceError(f"Data retrieval failed: {str(e)}") from e
    
    async def get_latest_glucose(
        self,
        access_token: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent glucose reading.
        
        Args:
            access_token: Valid OAuth2 access token
            
        Returns:
            Most recent glucose reading or None
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=1)
        readings = await self.get_glucose_readings(
            access_token, start_date, end_date
        )
        return max(readings, key=lambda r: r.get("systemTime", "")) if readings else None
    
    # -------------------------------------------------------------------
    # Data Ingestion
    # -------------------------------------------------------------------
    
    async def sync_glucose_data(
        self,
        session: AsyncSession,
        user: User,
        access_token: str,
        lookback_hours: int = 24,
    ) -> int:
        """Sync glucose data from Dexcom to local database.
        
        Retrieves latest glucose readings from Dexcom and saves them
        to the local database, avoiding duplicates.
        
        Args:
            session: Database session
            user: User to sync data for
            access_token: Valid OAuth2 access token
            lookback_hours: Hours of historical data to retrieve
            
        Returns:
            Number of new readings saved
            
        Raises:
            DexcomServiceError: If sync fails
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=lookback_hours)
        
        # Get existing reading timestamps to avoid duplicates
        from sqlalchemy import select
        existing = await session.execute(
            select(GlucoseReading.timestamp).where(
                GlucoseReading.user_id == user.id,
                GlucoseReading.source == "dexcom",
                GlucoseReading.timestamp >= start_date,
            )
        )
        existing_timestamps = {
            ts.replace(tzinfo=None) if ts.tzinfo else ts
            for ts in existing.scalars().all()
        }
        
        # Fetch from Dexcom
        raw_readings = await self.get_glucose_readings(
            access_token, start_date, end_date
        )
        
        new_readings = []
        trend_map = {
            "DoubleUp": "rising fast",
            "SingleUp": "rising",
            "FortyFiveUp": "rising slightly",
            "Flat": "steady",
            "FortyFiveDown": "falling slightly",
            "SingleDown": "falling",
            "DoubleDown": "falling fast",
        }
        
        for raw in raw_readings:
            try:
                reading_time = datetime.fromisoformat(
                    raw.get("systemTime", "").replace("Z", "+00:00")
                )
                # Normalize to naive UTC for comparison with SQLite-stored timestamps
                reading_time_naive = reading_time.replace(tzinfo=None)
                if reading_time_naive in existing_timestamps:
                    continue
                
                # Convert mg/dL to mmol/L if needed
                value_mg_dl = float(raw.get("value", 0))
                value_mmol_l = round(value_mg_dl / 18.016, 1)
                
                trend = raw.get("trend", "")
                trend_description = trend_map.get(trend, "")
                
                reading = GlucoseReading(
                    user_id=user.id,
                    glucose_value=value_mg_dl,
                    glucose_units="mg/dL",
                    timestamp=reading_time,
                    reading_type="sensor",
                    source="dexcom",
                    source_device_id="dexcom",
                    trend=trend_description,
                    trend_rate=None,  # Could calculate from previous readings
                    is_calibration=False,
                    is_filtered=False,
                    confidence_level=100,
                )
                new_readings.append(reading)
                
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Skipping invalid Dexcom reading: {e}")
                continue
        
        if new_readings:
            for reading in new_readings:
                session.add(reading)
            await session.commit()
            self.logger.info(
                f"Synced {len(new_readings)} glucose readings for user {user.id}"
            )
        
        return len(new_readings)
    
    async def sync_recent_data(
        self,
        session: AsyncSession,
        user: User,
        access_token: str,
    ) -> int:
        """Sync only the most recent glucose data (for frequent updates).
        
        Args:
            session: Database session
            user: User to sync data for
            access_token: Valid OAuth2 access token
            
        Returns:
            Number of new readings saved
        """
        return await self.sync_glucose_data(
            session, user, access_token, lookback_hours=1
        )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_trend_angle(trend_rate: Optional[float]) -> Optional[str]:
    """Convert trend rate to descriptive angle.
    
    Args:
        trend_rate: Glucose change rate in mg/dL per minute
        
    Returns:
        Descriptive trend angle or None
    """
    if trend_rate is None:
        return None
    if trend_rate >= 3.0:
        return "rising very fast"
    if trend_rate >= 2.0:
        return "rising fast"
    if trend_rate >= 1.0:
        return "rising"
    if trend_rate >= 0.5:
        return "rising slightly"
    if trend_rate <= -3.0:
        return "falling very fast"
    if trend_rate <= -2.0:
        return "falling fast"
    if trend_rate <= -1.0:
        return "falling"
    if trend_rate <= -0.5:
        return "falling slightly"
    return "steady"


def categorize_glucose_level(value: float) -> str:
    """Categorize glucose level into range.
    
    Args:
        value: Glucose value in mg/dL
        
    Returns:
        Category description
    """
    if value < 54:
        return "severe_low"
    if value < 70:
        return "low"
    if value <= 180:
        return "in_range"
    if value <= 250:
        return "high"
    return "severe_high"
