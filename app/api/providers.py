"""Connected provider status endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.metrics.models import HealthMetric

route = APIRouter(prefix="/providers", tags=["providers"])


class ProviderDetail(BaseModel):
    """Status for a single provider."""
    name: str = Field(..., description="Provider display name")
    key: str = Field(..., description="Provider key identifier")
    connected: bool = Field(..., description="Whether the provider has active data")
    last_sync: Optional[datetime] = Field(None, description="Last data sync timestamp")
    icon: str = Field(..., description="Lucide icon name")
    category: str = Field(..., description="Category: cgm, activity, sleep, weight")


class ProvidersStatusResponse(BaseModel):
    """Full provider status snapshot."""
    providers: list[ProviderDetail] = Field(..., description="All provider statuses")
    any_connected: bool = Field(..., description="Whether any provider is connected")


@route.get("/status", response_model=ProvidersStatusResponse)
async def get_providers_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> ProvidersStatusResponse:
    """Return connection status for all supported data providers.

    Checks user-level connections (Dexcom, Nightscout) and infers
    connectivity for activity/sleep/weight providers from recent
    health_metrics entries.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    # Infer connectivity from recent health_metric sources
    result = await db.execute(
        select(HealthMetric.source, func.max(HealthMetric.measured_at).label("last_at"))
        .where(
            HealthMetric.user_id == user.id,
            HealthMetric.measured_at >= cutoff,
        )
        .group_by(HealthMetric.source)
    )
    source_last_at = {row.source: row.last_at for row in result.all()}

    dexcom_connected = bool(
        user.dexcom_access_token and user.dexcom_expires_at and user.dexcom_expires_at > datetime.now(timezone.utc)
    )

    providers = [
        ProviderDetail(
            name="Dexcom",
            key="dexcom",
            connected=dexcom_connected,
            last_sync=user.last_glucose_sync,
            icon="Activity",
            category="cgm",
        ),
        ProviderDetail(
            name="Nightscout",
            key="nightscout",
            connected=user.nightscout_connected,
            last_sync=user.last_nightscout_sync,
            icon="Globe",
            category="cgm",
        ),
        ProviderDetail(
            name="LibreLinkUp",
            key="librelinkup",
            connected=user.librelinkup_connected,
            last_sync=user.last_librelinkup_sync,
            icon="Activity",
            category="cgm",
        ),
        ProviderDetail(
            name="Garmin Connect",
            key="garmin",
            connected="garmin" in source_last_at,
            last_sync=source_last_at.get("garmin"),
            icon="Watch",
            category="activity",
        ),
        ProviderDetail(
            name="Fitbit",
            key="fitbit",
            connected="fitbit" in source_last_at,
            last_sync=source_last_at.get("fitbit"),
            icon="Heart",
            category="activity",
        ),
        ProviderDetail(
            name="Strava",
            key="strava",
            connected="strava" in source_last_at,
            last_sync=source_last_at.get("strava"),
            icon="Bike",
            category="activity",
        ),
        ProviderDetail(
            name="Withings",
            key="withings",
            connected="withings" in source_last_at,
            last_sync=source_last_at.get("withings"),
            icon="Scale",
            category="weight",
        ),
        ProviderDetail(
            name="Polar",
            key="polar",
            connected="polar" in source_last_at,
            last_sync=source_last_at.get("polar"),
            icon="HeartPulse",
            category="activity",
        ),
        ProviderDetail(
            name="Manual entry",
            key="manual",
            connected=True,
            last_sync=None,
            icon="Pencil",
            category="other",
        ),
    ]

    return ProvidersStatusResponse(
        providers=providers,
        any_connected=any(p.connected for p in providers),
    )
