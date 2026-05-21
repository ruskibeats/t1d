"""LibreLinkUp API integration service.

Direct connection to Abbott's LibreView/LibreLinkUp API.
Bypasses the need for a Nightscout instance for development/testing.

Reference: Reverse-engineered from LibreLinkUp iOS app API patterns.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.database import AsyncSession
from app.db.models import GlucoseReading, User

logger = logging.getLogger(__name__)

# LibreLinkUp API endpoints by region
LLU_API_ENDPOINTS = {
    "AE": "api-ae.libreview.io",
    "AP": "api-ap.libreview.io",
    "AU": "api-au.libreview.io",
    "CA": "api-ca.libreview.io",
    "DE": "api-de.libreview.io",
    "EU": "api-eu.libreview.io",
    "EU2": "api-eu2.libreview.io",
    "FR": "api-fr.libreview.io",
    "JP": "api-jp.libreview.io",
    "US": "api-us.libreview.io",
    "LA": "api-la.libreview.io",
    "RU": "api.libreview.ru",
    "CN": "api-cn.myfreestyle.cn",
}


class LibreLinkUpConfig(BaseModel):
    """Configuration for LibreLinkUp connection."""
    
    email: str
    password: str
    region: str = Field(default="EU2", description="LibreLinkUp region (EU2, US, etc.)")
    version: str = Field(default="4.16.0", description="API version header")


class LibreLinkUpAuthTicket(BaseModel):
    """Authentication ticket from LibreLinkUp."""
    
    token: str
    expires: int
    duration: int


class LibreLinkUpGlucoseReading(BaseModel):
    """A single glucose reading from LibreLinkUp."""
    
    timestamp: datetime
    factory_timestamp: datetime
    value_mg_dl: float
    trend_arrow: Optional[int] = None
    measurement_color: int
    is_high: bool
    is_low: bool

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "LibreLinkUpGlucoseReading":
        """Create reading from LibreLinkUp API response data.
        
        The API returns US-format timestamps like '5/20/2026 11:27:23 AM'
        which need custom parsing.
        """
        ts_str = data.get("Timestamp", "")
        ft_str = data.get("FactoryTimestamp", "")
        
        def _parse_ts(s: str) -> datetime:
            # Try ISO 8601 first
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T"))
            except (ValueError, TypeError):
                pass
            # Try US format: "M/D/YYYY H:MM:SS AM/PM"
            try:
                return datetime.strptime(s.strip(), "%m/%d/%Y %I:%M:%S %p")
            except (ValueError, TypeError):
                pass
            raise ValueError(f"Unable to parse timestamp: {s}")
        
        return cls(
            timestamp=_parse_ts(ts_str),
            factory_timestamp=_parse_ts(ft_str),
            value_mg_dl=float(data.get("ValueInMgPerDl", 0)),
            trend_arrow=data.get("TrendArrow"),
            measurement_color=int(data.get("MeasurementColor", 0)),
            is_high=bool(data.get("isHigh", False)),
            is_low=bool(data.get("isLow", False)),
        )


class LibreLinkUpServiceError(Exception):
    """Raised when LibreLinkUp API communication fails."""
    pass


class LibreLinkUpService:
    """Service for LibreLinkUp (LibreView) API integration.
    
    Connects directly to Abbott's LibreLinkUp API to fetch glucose
    data from Freestyle Libre sensors, bypassing Nightscout.
    """
    
    def __init__(
        self,
        email: str,
        password: str,
        region: str = "EU2",
        version: str = "4.16.0",
    ):
        """Initialize LibreLinkUp service.
        
        Args:
            email: LibreLinkUp account email
            password: LibreLinkUp account password
            region: API region (EU2, US, etc.)
            version: API version header
        """
        self.email = email
        self.password = password
        self.region = region
        self.version = version
        self.base_url = LLU_API_ENDPOINTS.get(region, "api-eu2.libreview.io")
        self.logger = logging.getLogger(f"{__name__}.LibreLinkUpService")
        
        self._auth_ticket: Optional[LibreLinkUpAuthTicket] = None
        self._user_id: Optional[str] = None
        self._patient_id: Optional[str] = None
    
    def _build_headers(self, auth: bool = False) -> Dict[str, str]:
        """Build HTTP headers for LibreLinkUp API requests.
        
        Args:
            auth: Whether to include authentication headers
            
        Returns:
            Headers dictionary
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU OS 17_4.1 like Mac OS X) "
                "AppleWebKit/536.26 (KHTML, like Gecko) "
                "Version/17.4.1 Mobile/10A5355d Safari/8536.25"
            ),
            "Content-Type": "application/json;charset=UTF-8",
            "version": self.version,
            "product": "llu.ios",
        }
        
        if auth and self._auth_ticket:
            headers["Authorization"] = f"Bearer {self._auth_ticket.token}"
            if self._user_id:
                headers["account-id"] = hashlib.sha256(
                    self._user_id.encode()
                ).hexdigest()
        
        return headers
    
    def _get_client(self) -> httpx.AsyncClient:
        """Create an HTTPX client with cookie support.
        
        Returns:
            Configured httpx AsyncClient with cookie jar
        """
        return httpx.AsyncClient(
            base_url=f"https://{self.base_url}",
            headers=self._build_headers(),
            timeout=30.0,
            cookies={},  # Let httpx handle cookies
        )
    
    # -------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------
    
    async def login(self) -> LibreLinkUpAuthTicket:
        """Authenticate with LibreLinkUp API.
        
        Returns:
            Auth ticket with bearer token
            
        Raises:
            LibreLinkUpServiceError: If login fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"https://{self.base_url}/llu/auth/login"
                response = await client.post(
                    url,
                    json={"email": self.email, "password": self.password},
                    headers=self._build_headers(),
                )
                
                data = response.json()
                
                if response.status_code != 200 or data.get("status") != 0:
                    if data.get("status") == 920:
                        min_ver = data.get("data", {}).get("minimumVersion", "unknown")
                        raise LibreLinkUpServiceError(
                            f"API version mismatch. Minimum required: {min_ver}. "
                            f"Set version to {min_ver}."
                        )
                    raise LibreLinkUpServiceError(
                        f"Login failed: {data.get('message', 'Unknown error')}"
                    )
                
                # Check if we logged into the wrong region
                if data.get("data", {}).get("redirect") and data.get("data", {}).get("region"):
                    correct_region = data["data"]["region"].upper()
                    self.logger.warning(
                        f"Logged into wrong region '{self.region}', "
                        f"should be '{correct_region}'. Updating."
                    )
                    self.region = correct_region
                    self.base_url = LLU_API_ENDPOINTS.get(
                        correct_region, self.base_url
                    )
                    # Retry login with correct region
                    return await self.login()
                
                auth_data = data["data"]["authTicket"]
                self._auth_ticket = LibreLinkUpAuthTicket(
                    token=auth_data["token"],
                    expires=auth_data["expires"],
                    duration=auth_data["duration"],
                )
                self._user_id = data["data"]["user"]["id"]
                
                self.logger.info(
                    f"Logged into LibreLinkUp ({self.region}) "
                    f"as {data['data']['user']['firstName']} "
                    f"{data['data']['user']['lastName']}"
                )
                
                return self._auth_ticket
                
            except httpx.HTTPStatusError as e:
                raise LibreLinkUpServiceError(
                    f"Login HTTP error: {e.response.text[:200]}"
                ) from e
            except LibreLinkUpServiceError:
                raise
            except Exception as e:
                raise LibreLinkUpServiceError(
                    f"Login failed: {str(e)}"
                ) from e
    
    async def ensure_authenticated(self) -> None:
        """Ensure we have a valid auth ticket, logging in if needed."""
        if not self._auth_ticket:
            await self.login()
    
    # -------------------------------------------------------------------
    # Data Retrieval
    # -------------------------------------------------------------------
    
    async def get_patient_id(self) -> str:
        """Get the connected patient ID from LibreLinkUp.
        
        Returns:
            Patient ID string
            
        Raises:
            LibreLinkUpServiceError: If no connections found
        """
        await self.ensure_authenticated()
        
        headers = self._build_headers(auth=True)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"https://{self.base_url}/llu/connections"
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200 or data.get("status") != 0:
                    raise LibreLinkUpServiceError(
                        f"Failed to get connections: {data.get('message', 'Unknown error')}"
                    )
                
                connections = data.get("data", [])
                if not connections:
                    raise LibreLinkUpServiceError(
                        "No LibreLinkUp connections found. "
                        "Make sure someone has shared their data with this account."
                    )
                
                # Use the first connection (most common for personal use)
                connection = connections[0]
                self._patient_id = connection["patientId"]
                self.logger.info(
                    f"Found connection: {connection.get('firstName', 'Unknown')} "
                    f"{connection.get('lastName', '')} "
                    f"(patientId: {self._patient_id})"
                )
                
                return self._patient_id
                
            except httpx.HTTPStatusError as e:
                raise LibreLinkUpServiceError(
                    f"Connection list HTTP error: {e.response.text[:200]}"
                ) from e
            except LibreLinkUpServiceError:
                raise
            except Exception as e:
                raise LibreLinkUpServiceError(
                    f"Failed to get patient ID: {str(e)}"
                ) from e
    
    async def get_glucose_graph(self) -> Dict[str, Any]:
        """Fetch glucose graph data from LibreLinkUp.
        
        Returns:
            Graph data containing readings, active sensors, etc.
            
        Raises:
            LibreLinkUpServiceError: If data retrieval fails
        """
        await self.ensure_authenticated()
        
        if not self._patient_id:
            await self.get_patient_id()
        
        headers = self._build_headers(auth=True)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = (
                    f"https://{self.base_url}/llu/connections/"
                    f"{self._patient_id}/graph"
                )
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200 or data.get("status") != 0:
                    raise LibreLinkUpServiceError(
                        f"Failed to get glucose graph: "
                        f"{data.get('message', 'Unknown error')}"
                    )
                
                return data.get("data", {})
                
            except httpx.HTTPStatusError as e:
                raise LibreLinkUpServiceError(
                    f"Graph data HTTP error: {e.response.text[:200]}"
                ) from e
            except LibreLinkUpServiceError:
                raise
            except Exception as e:
                raise LibreLinkUpServiceError(
                    f"Failed to get glucose data: {str(e)}"
                ) from e
    
    async def get_glucose_readings(
        self,
        max_count: int = 100,
    ) -> List[LibreLinkUpGlucoseReading]:
        """Get recent glucose readings from LibreLinkUp.
        
        Args:
            max_count: Maximum number of readings to return
            
        Returns:
            List of glucose readings (newest first)
        """
        graph = await self.get_glucose_graph()
        raw_readings = graph.get("graphData", [])
        
        # LibreLinkUp returns newest first
        readings = []
        for raw in raw_readings[:max_count]:
            try:
                readings.append(LibreLinkUpGlucoseReading.from_api(raw))
            except Exception as e:
                self.logger.warning(f"Skipping invalid reading: {e}")
                continue
        
        return readings
    
    async def get_latest_glucose(self) -> Optional[LibreLinkUpGlucoseReading]:
        """Get the most recent glucose reading.
        
        Returns:
            Most recent reading or None
        """
        readings = await self.get_glucose_readings(max_count=1)
        return readings[0] if readings else None
    
    # -------------------------------------------------------------------
    # Data Ingestion (Sync to local DB)
    # -------------------------------------------------------------------
    
    def _trend_arrow_to_description(self, arrow: Optional[int]) -> str:
        """Convert LibreLinkUp trend arrow to description.
        
        Args:
            arrow: Trend arrow value (1-5)
            
        Returns:
            Human-readable trend description
        """
        trend_map = {
            1: "falling fast",
            2: "falling slightly",
            3: "steady",
            4: "rising slightly",
            5: "rising fast",
        }
        return trend_map.get(arrow or 3, "unknown")
    
    async def sync_glucose_data(
        self,
        session: AsyncSession,
        user: User,
        lookback_hours: int = 24,
    ) -> int:
        """Sync glucose data from LibreLinkUp to local database.
        
        Args:
            session: Database session
            user: User to sync data for
            lookback_hours: Hours of historical data to retrieve
            
        Returns:
            Number of new readings saved
            
        Raises:
            LibreLinkUpServiceError: If sync fails
        """
        from sqlalchemy import select
        
        readings = await self.get_glucose_readings(max_count=1000)
        
        now = datetime.now(timezone.utc)
        cutoff = now.replace(tzinfo=None)  # DB stores naive UTC
        
        # Get existing timestamps to avoid duplicates
        existing = await session.execute(
            select(GlucoseReading.timestamp).where(
                GlucoseReading.user_id == user.id,
                GlucoseReading.source == "libre",
                GlucoseReading.timestamp >= cutoff.replace(hour=0, minute=0, second=0),
            )
        )
        existing_timestamps = set(existing.scalars().all())
        
        new_readings = []
        for reading in readings:
            reading_time = reading.timestamp.replace(tzinfo=None)
            
            if reading_time in existing_timestamps:
                continue
            if reading_time < cutoff.replace(hour=cutoff.hour - lookback_hours):
                continue
            
            trend_description = self._trend_arrow_to_description(reading.trend_arrow)
            
            db_reading = GlucoseReading(
                user_id=user.id,
                glucose_value=reading.value_mg_dl,
                glucose_units="mg/dL",
                timestamp=reading_time,
                reading_type="sensor",
                source="libre",
                source_device_id="librelinkup",
                trend=trend_description,
                trend_rate=None,
                is_calibration=False,
                is_filtered=False,
                confidence_level=100,
            )
            new_readings.append(db_reading)
        
        if new_readings:
            for r in new_readings:
                session.add(r)
            await session.commit()
            self.logger.info(
                f"Synced {len(new_readings)} LibreLinkUp readings "
                f"for user {user.id}"
            )
        
        return len(new_readings)
    
    async def sync_recent_data(
        self,
        session: AsyncSession,
        user: User,
    ) -> int:
        """Sync only the most recent glucose data.
        
        Args:
            session: Database session
            user: User to sync data for
            
        Returns:
            Number of new readings saved
        """
        return await self.sync_glucose_data(
            session, user, lookback_hours=1
        )