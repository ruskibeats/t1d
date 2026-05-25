"""Nightscout API integration service.

Handles data retrieval from Nightscout open-source CGM systems.
Reference: https://nightscout.github.io/
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
from app.services.glucose_converter import to_mmol, format_glucose


logger = logging.getLogger(__name__)


class NightscoutGlucoseReading(BaseModel):
    """Nightscout glucose reading format."""
    
    id: str = Field(..., alias="_id", description="MongoDB object ID")
    date: int = Field(..., description="Unix timestamp in milliseconds")
    sgv: int = Field(..., description="Sensor glucose value in mg/dL")
    direction: Optional[str] = Field(None, description="Trend direction")
    device: Optional[str] = Field(None, description="Device identifier")
    type: Optional[str] = Field(None, description="Entry type")
    filtered: Optional[float] = Field(None, description="Filtered value")
    unfiltered: Optional[float] = Field(None, description="Unfiltered value")
    rssi: Optional[int] = Field(None, description="Signal strength")
    noise: Optional[str] = Field(None, description="Noise level")


class NightscoutServiceError(Exception):
    """Raised when Nightscout API communication fails."""
    pass


class NightscoutService:
    """Service for Nightscout API integration.
    
    Handles data retrieval from open-source Nightscout CGM systems.
    Supports multiple authentication methods (token, basic auth, or none).
    """
    
    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        """Initialize Nightscout service.
        
        Args:
            base_url: Nightscout base URL (e.g., https://my-ns.herokuapp.com)
            api_token: API token for authentication (optional)
            username: Basic auth username (optional)
            password: Basic auth password (optional)
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.logger = logging.getLogger(f"{__name__}.NightscoutService")
    
    # -------------------------------------------------------------------
    # Internal HTTP Methods
    # -------------------------------------------------------------------
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.
        
        Returns:
            Dictionary of authentication headers
        """
        headers = {"Content-Type": "application/json"}
        
        if self.api_token:
            headers["api-secret"] = self.api_token
        elif self.username and self.password:
            # Basic auth handled by httpx
            pass
        
        return headers
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Create authenticated HTTP client.
        
        Returns:
            Configured httpx AsyncClient
        """
        auth = None
        if self.username and self.password:
            auth = httpx.BasicAuth(self.username, self.password)
        
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._get_auth_headers(),
            auth=auth,
            timeout=30.0,
            verify=self.verify_ssl,
        )
    
    async def _test_connection(self) -> bool:
        """Test connection to Nightscout instance.
        
        Returns:
            True if connection succeeds
            
        Raises:
            NightscoutServiceError: If connection test fails
        """
        async with await self._get_client() as client:
            try:
                response = await client.get("/api/v2/status")
                response.raise_for_status()
                return True
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Nightscout connection test failed: {e}")
                raise NightscoutServiceError(
                    f"Failed to connect to Nightscout: {e.response.text}"
                ) from e
            except Exception as e:
                self.logger.error(f"Nightscout connection error: {e}")
                raise NightscoutServiceError(
                    f"Connection test failed: {str(e)}"
                ) from e
    
    # -------------------------------------------------------------------
    # Data Retrieval
    # -------------------------------------------------------------------
    
    async def get_glucose_readings(
        self,
        start_date: datetime,
        end_date: datetime,
        max_count: int = 1000,
    ) -> List[NightscoutGlucoseReading]:
        """Retrieve glucose readings from Nightscout API.
        
        Uses the /api/v1/entries endpoint to fetch sgv (sensor glucose) data.
        
        Args:
            start_date: Start of date range (UTC)
            end_date: End of date range (UTC)
            max_count: Maximum number of readings to retrieve
            
        Returns:
            List of glucose readings from Nightscout
            
        Raises:
            NightscoutServiceError: If data retrieval fails
        """
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        
        params = {
            "count": max_count,
            "find[date][$gte]": start_ms,
            "find[date][$lte]": end_ms,
            "sort[date]": 1,  # Ascending
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        async with await self._get_client() as client:
            try:
                response = await client.get(
                    "/api/v1/entries.json",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                
                if not isinstance(data, list):
                    self.logger.error(f"Unexpected Nightscout response: {data}")
                    return []
                
                return [NightscoutGlucoseReading(**item) for item in data]
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Nightscout data retrieval failed: {e}")
                if e.response.status_code == 401:
                    raise NightscoutServiceError(
                        "Authentication failed. Check API token or credentials."
                    ) from e
                raise NightscoutServiceError(
                    f"Failed to retrieve glucose data: {e.response.text}"
                ) from e
            except Exception as e:
                self.logger.error(f"Nightscout data retrieval error: {e}")
                raise NightscoutServiceError(
                    f"Data retrieval failed: {str(e)}"
                ) from e
    
    async def get_latest_glucose(
        self,
    ) -> Optional[NightscoutGlucoseReading]:
        """Retrieve the most recent glucose reading.
        
        Returns:
            Most recent glucose reading or None
        """
        readings = await self.get_glucose_readings(
            start_date=datetime.now(timezone.utc) - timedelta(hours=1),
            end_date=datetime.now(timezone.utc),
            max_count=1,
        )
        return readings[0] if readings else None

    def display_glucose(self, reading: NightscoutGlucoseReading | None, unit: str = "mmol/L") -> str:
        """Format a glucose reading in the user's preferred units."""
        if not reading:
            return "N/A"
        return format_glucose(float(reading.sgv), unit)

    # -------------------------------------------------------------------
    # Data Ingestion
    # -------------------------------------------------------------------
    
    async def sync_glucose_data(
        self,
        session: AsyncSession,
        user: User,
        lookback_hours: int = 24,
    ) -> int:
        """Sync glucose data from Nightscout to local database.
        
        Retrieves latest glucose readings from Nightscout and saves them
        to the local database, avoiding duplicates.
        
        Args:
            session: Database session
            user: User to sync data for
            lookback_hours: Hours of historical data to retrieve
            
        Returns:
            Number of new readings saved
            
        Raises:
            NightscoutServiceError: If sync fails
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=lookback_hours)
        
        # Test connection first
        await self._test_connection()
        
        # Get existing reading timestamps to avoid duplicates
        from sqlalchemy import select
        existing = await session.execute(
            select(GlucoseReading.timestamp).where(
                GlucoseReading.user_id == user.id,
                GlucoseReading.source.in_(["nightscout", "nightscout-unknown"]),
                GlucoseReading.timestamp >= start_date,
            )
        )
        existing_timestamps = set(existing.scalars().all())
        
        # Fetch from Nightscout
        raw_readings = await self.get_glucose_readings(
            start_date, end_date
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
            "NONE": "unknown",
        }
        
        for raw in raw_readings:
            try:
                reading_time = datetime.fromtimestamp(
                    raw.date / 1000, tz=timezone.utc
                )
                if reading_time in existing_timestamps:
                    continue
                
                value_mg_dl = float(raw.sgv)
                direction = raw.direction or ""
                trend_description = trend_map.get(direction, "")
                
                # Determine source device
                source_device = raw.device or "nightscout"
                
                reading = GlucoseReading(
                    user_id=user.id,
                    glucose_value=value_mg_dl,
                    glucose_units="mg/dL",
                    timestamp=reading_time,
                    reading_type="sensor",
                    source="nightscout",
                    source_device_id=source_device,
                    trend=trend_description,
                    trend_rate=None,
                    is_calibration=False,
                    is_filtered=raw.filtered is not None,
                    confidence_level=100,
                )
                new_readings.append(reading)
                
            except (ValueError, KeyError, AttributeError) as e:
                self.logger.warning(f"Skipping invalid Nightscout reading: {e}")
                continue
        
        if new_readings:
            for reading in new_readings:
                session.add(reading)
            await session.commit()
            self.logger.info(
                f"Synced {len(new_readings)} glucose readings "
                f"from Nightscout for user {user.id}"
            )
        
        return len(new_readings)
    
    async def sync_recent_data(
        self,
        session: AsyncSession,
        user: User,
    ) -> int:
        """Sync only the most recent glucose data (for frequent updates).
        
        Args:
            session: Database session
            user: User to sync data for
            
        Returns:
            Number of new readings saved
        """
        return await self.sync_glucose_data(
            session, user, lookback_hours=1
        )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def parse_nightscout_direction(direction: Optional[str]) -> str:
    """Convert Nightscout direction to descriptive text.
    
    Args:
        direction: Nightscout direction string
        
    Returns:
        Human-readable trend description
    """
    if not direction:
        return "unknown"
    
    map_dict = {
        "DoubleUp": "rising very fast",
        "SingleUp": "rising fast",
        "FortyFiveUp": "rising moderately",
        "Flat": "steady",
        "FortyFiveDown": "falling moderately",
        "SingleDown": "falling fast",
        "DoubleDown": "falling very fast",
        "NONE": "unknown",
    }
    return map_dict.get(direction, f"trending {direction}")


def estimate_trend_rate(direction: Optional[str]) -> Optional[float]:
    """Estimate trend rate from Nightscout direction.
    
    Rough estimates for visualization purposes.
    
    Args:
        direction: Nightscout direction string
        
    Returns:
        Estimated trend rate in mg/dL per minute
    """
    rate_map = {
        "DoubleUp": 3.5,
        "SingleUp": 2.0,
        "FortyFiveUp": 1.0,
        "Flat": 0.0,
        "FortyFiveDown": -1.0,
        "SingleDown": -2.0,
        "DoubleDown": -3.5,
    }
    return rate_map.get(direction or "")
