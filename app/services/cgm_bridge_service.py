"""Unified CGM Bridge Service.

Seamless multi-source CGM data ingestion. The user sees one "Connect CGM" button
— they never need to know whether their data comes from Dexcom, LibreLinkUp,
or a hosted Nightscout instance.

Architecture:
```
User clicks "Connect CGM"
        ↓
  CgmBridgeService.connect(source_type, credentials)
        ↓
  ┌─── Dexcom OAuth ─────┐
  ├─── LibreLinkUp direct ┤
  ├─── Hosted Nightscout ─┤  ← future: auto-provisioned
  └──────────────────────┘
        ↓
  Unified glucose data → PostgreSQL
        ↓
  User sees data in app (no URLs, no servers visible)
```
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Types ──


class CgmSource(str, Enum):
    """Supported CGM data sources."""
    DEXCOM = "dexcom"
    LIBRELINKUP = "librelinkup"
    NIGHTSCOUT = "nightscout"


@dataclass
class CgmConnectionConfig:
    """Connection configuration for a CGM source."""
    source: CgmSource
    user_id: int

    # Dexcom OAuth
    dexcom_access_token: Optional[str] = None
    dexcom_refresh_token: Optional[str] = None

    # LibreLinkUp
    librelinkup_email: Optional[str] = None
    librelinkup_password: Optional[str] = None
    librelinkup_region: str = "EU2"

    # Nightscout
    nightscout_url: Optional[str] = None
    nightscout_api_token: Optional[str] = None

    # Hosted Nightscout (auto-provisioned)
    hosted_ns_url: Optional[str] = None
    hosted_ns_token: Optional[str] = None


@dataclass
class CgmConnectionResult:
    """Result of a CGM connection attempt."""
    success: bool
    source: CgmSource
    message: str
    requires_consent: bool = False  # True for LibreLinkUp (reverse-engineered)
    consent_text: str = ""

    # Hosted Nightscout provisioning
    provisioned_url: Optional[str] = None
    provisioned_token: Optional[str] = None


@dataclass
class GlucoseRecord:
    """Unified glucose reading from any source."""
    value_mgdl: float
    timestamp: datetime
    source: CgmSource
    trend: Optional[str] = None  # "flat", "rising", "falling", etc.
    trend_rate: Optional[float] = None  # mg/dL per minute
    source_device_id: Optional[str] = None


# ── Source adapters ──


class CgmSourceAdapter(ABC):
    """Abstract adapter for a CGM data source."""

    @abstractmethod
    async def test_connection(self, config: CgmConnectionConfig) -> CgmConnectionResult:
        """Test if the connection works."""
        ...

    @abstractmethod
    async def fetch_readings(
        self,
        config: CgmConnectionConfig,
        minutes_back: int = 60 * 24,  # 24 hours
    ) -> list[GlucoseRecord]:
        """Fetch recent glucose readings."""
        ...

    @abstractmethod
    async def disconnect(self, config: CgmConnectionConfig) -> bool:
        """Disconnect and revoke access."""
        ...


class DexcomAdapter(CgmSourceAdapter):
    """Official Dexcom OAuth integration."""

    async def test_connection(self, config: CgmConnectionConfig) -> CgmConnectionResult:
        if not config.dexcom_access_token:
            return CgmConnectionResult(
                success=False,
                source=CgmSource.DEXCOM,
                message="No Dexcom access token configured.",
            )
        # Token validation happens via DexcomService
        return CgmConnectionResult(
            success=True,
            source=CgmSource.DEXCOM,
            message="Dexcom connected.",
        )

    async def fetch_readings(
        self,
        config: CgmConnectionConfig,
        minutes_back: int = 60 * 24,
    ) -> list[GlucoseRecord]:
        from app.services.dexcom_service import DexcomService
        from app.config import get_settings

        settings = get_settings()
        dexcom = DexcomService(
            client_id=settings.dexcom_client_id,
            client_secret=settings.dexcom_client_secret,
            redirect_uri=settings.dexcom_redirect_uri,
            use_sandbox=settings.dexcom_use_sandbox,
        )
        # DexcomService reads using stored tokens on the User model
        # This is handled by the existing sync flow
        return []

    async def disconnect(self, config: CgmConnectionConfig) -> bool:
        return True


class LibreLinkUpAdapter(CgmSourceAdapter):
    """LibreLinkUp direct integration (reverse-engineered API)."""

    async def test_connection(self, config: CgmConnectionConfig) -> CgmConnectionResult:
        if not config.librelinkup_email or not config.librelinkup_password:
            return CgmConnectionResult(
                success=False,
                source=CgmSource.LIBRELINKUP,
                message="Email and password required.",
            )

        from app.services.librelinkup_service import LibreLinkUpService

        try:
            service = LibreLinkUpService(
                email=config.librelinkup_email,
                password=config.librelinkup_password,
                region=config.librelinkup_region,
            )
            readings = await service.fetch_recent(version="4.16.0")
            if readings:
                return CgmConnectionResult(
                    success=True,
                    source=CgmSource.LIBRELINKUP,
                    message=f"Connected. Found {len(readings)} recent readings.",
                    requires_consent=True,
                    consent_text=(
                        "This connects via LibreLinkUp, which uses a community-maintained "
                        "API (not officially supported by Abbott). Your data is stored "
                        "securely and used only for educational insights."
                    ),
                )
            return CgmConnectionResult(
                success=False,
                source=CgmSource.LIBRELINKUP,
                message="Connected but no readings found. Check your LibreLinkUp account.",
            )
        except Exception as e:
            return CgmConnectionResult(
                success=False,
                source=CgmSource.LIBRELINKUP,
                message=f"Connection failed: {e}",
            )

    async def fetch_readings(
        self,
        config: CgmConnectionConfig,
        minutes_back: int = 60 * 24,
    ) -> list[GlucoseRecord]:
        # Handled by existing sync_service.py
        return []

    async def disconnect(self, config: CgmConnectionConfig) -> bool:
        return True


class HostedNightscoutAdapter(CgmSourceAdapter):
    """Auto-provisioned hosted Nightscout instance.

    Each user gets a unique NS URL + API token on a shared server.
    The user never sees the URL — it's handled by the bridge.
    """

    async def test_connection(self, config: CgmConnectionConfig) -> CgmConnectionResult:
        # For hosted NS, we provision on connect
        return CgmConnectionResult(
            success=True,
            source=CgmSource.NIGHTSCOUT,
            message="Hosted Nightscout ready.",
            provisioned_url=config.hosted_ns_url,
            provisioned_token=config.hosted_ns_token,
        )

    async def fetch_readings(
        self,
        config: CgmConnectionConfig,
        minutes_back: int = 60 * 24,
    ) -> list[GlucoseRecord]:
        if not config.nightscout_url:
            return []
        from app.services.nightscout_service import NightscoutService
        try:
            service = NightscoutService(config.nightscout_url, config.nightscout_api_token)
            return await service.fetch_recent(minutes_back=minutes_back)
        except Exception:
            return []

    async def disconnect(self, config: CgmConnectionConfig) -> bool:
        return True


# ── Bridge service ──


class CgmBridgeService:
    """Unified CGM connection manager.

    Presents a single "Connect CGM" interface to the frontend.
    Handles all source types transparently.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._adapters: dict[CgmSource, CgmSourceAdapter] = {
            CgmSource.DEXCOM: DexcomAdapter(),
            CgmSource.LIBRELINKUP: LibreLinkUpAdapter(),
            CgmSource.NIGHTSCOUT: HostedNightscoutAdapter(),
        }

    async def get_available_sources(self) -> list[dict[str, Any]]:
        """Return available CGM sources with descriptions for the UI."""
        return [
            {
                "id": "dexcom",
                "name": "Dexcom",
                "description": "Official OAuth integration. Supports G6 and G7.",
                "requires_setup": False,
                "requires_consent": False,
                "is_recommended": True,
                "setup_url": None,
            },
            {
                "id": "librelinkup",
                "name": "LibreLinkUp (Libre)",
                "description": "Direct connection for FreeStyle Libre users.",
                "requires_setup": False,
                "requires_consent": True,
                "is_recommended": True,
                "setup_url": None,
            },
            {
                "id": "nightscout",
                "name": "Nightscout",
                "description": "For users who already run Nightscout.",
                "requires_setup": True,
                "requires_consent": False,
                "is_recommended": False,
                "setup_url": "/docs/NIGHTSCOUT_SETUP.md",
            },
        ]

    async def connect(
        self,
        source: CgmSource,
        user_id: int,
        **credentials,
    ) -> CgmConnectionResult:
        """Connect a CGM source.

        The user-facing API is just: connect("dexcom", user_id, ...) or
        connect("librelinkup", user_id, email=..., password=..., region=...).
        Everything else is handled internally.
        """
        adapter = self._adapters.get(source)
        if not adapter:
            return CgmConnectionResult(
                success=False,
                source=source,
                message=f"Unsupported CGM source: {source}",
            )

        config = CgmConnectionConfig(source=source, user_id=user_id, **credentials)
        result = await adapter.test_connection(config)

        if result.success:
            logger.info(
                f"CGM Bridge: {source.value} connected for user {user_id}"
            )

        return result

    async def get_connected_sources(self, user) -> list[dict[str, Any]]:
        """Get all connected sources for a user."""
        sources = []
        if user.dexcom_access_token:
            sources.append({
                "id": "dexcom",
                "name": "Dexcom",
                "connected": True,
            })
        if user.librelinkup_email:
            sources.append({
                "id": "librelinkup",
                "name": "LibreLinkUp",
                "connected": True,
            })
        if user.nightscout_url:
            sources.append({
                "id": "nightscout",
                "name": "Nightscout",
                "connected": True,
                "url": user.nightscout_url,
            })
        return sources

    async def disconnect(self, source: CgmSource, user) -> bool:
        """Disconnect a CGM source and clean up."""
        adapter = self._adapters.get(source)
        if adapter:
            config = CgmConnectionConfig(source=source, user_id=user.id)
            await adapter.disconnect(config)

        # Clear stored credentials
        if source == CgmSource.DEXCOM:
            user.dexcom_access_token = None
            user.dexcom_refresh_token = None
            user.dexcom_expires_at = None
        elif source == CgmSource.LIBRELINKUP:
            user.librelinkup_email = None
            user.librelinkup_password = None
        elif source == CgmSource.NIGHTSCOUT:
            user.nightscout_url = None
            user.nightscout_api_token = None

        await self.session.commit()
        logger.info(f"CGM Bridge: {source.value} disconnected for user {user.id}")
        return True