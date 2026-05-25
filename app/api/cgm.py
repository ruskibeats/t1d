"""CGM (Continuous Glucose Monitor) connection API.

Seamless Dexcom OAuth and Nightscout connection endpoints.
Lets users connect/disconnect their CGM sources from the frontend.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.models.user import (
    CGMConnectionStatus,
    CGMConnectResponse,
    DexcomAuthUrlResponse,
    DexcomConnectionDetail,
    LibreLinkUpConnectionDetail,
    LibreLinkUpTestResult,
    NightscoutConnectionDetail,
    NightscoutTestResult,
)
from app.services.sync_service import trigger_manual_sync

logger = logging.getLogger(__name__)

route = APIRouter()


# ── Schemas ──


class LibreLinkUpConnectRequest(BaseModel):
    """Request to connect LibreLinkUp."""
    email: str = Field(..., description="LibreLinkUp account email")
    password: str = Field(..., description="LibreLinkUp account password")
    region: str = Field("EU2", description="LibreLinkUp API region (EU2, US, etc.)")


class LibreLinkUpDisconnectResponse(BaseModel):
    """Response after disconnecting LibreLinkUp."""
    success: bool = Field(..., description="Whether the disconnection was successful")
    message: str = Field(..., description="Human-readable message")


class NightscoutConnectRequest(BaseModel):
    """Request to connect a Nightscout instance."""
    url: str = Field(..., description="Nightscout base URL (e.g. https://my-ns.herokuapp.com)")
    api_token: str | None = Field(None, description="Nightscout API token (optional if public)")


class NightscoutDisconnectResponse(BaseModel):
    """Response after disconnecting Nightscout."""
    success: bool = Field(..., description="Whether the disconnection was successful")
    message: str = Field(..., description="Human-readable message")


class CgmConnectRequest(BaseModel):
    """Unified CGM connection request."""
    source: str = Field(..., description="cgm source: dexcom, librelinkup, or nightscout")
    email: str | None = Field(None, description="email (for librelinkup)")
    password: str | None = Field(None, description="password (for librelinkup)")
    region: str = Field("EU2", description="region (for librelinkup)")
    url: str | None = Field(None, description="nightscout URL")
    api_token: str | None = Field(None, description="nightscout API token")
    consent_given: bool = Field(False, description="user accepted disclaimer (required for librelinkup)")


class CgmSourceInfo(BaseModel):
    """Available CGM source descriptor for the UI."""
    id: str
    name: str
    description: str
    requires_setup: bool
    requires_consent: bool
    is_recommended: bool
    setup_url: str | None = None


# ── Helpers ──


def _get_dexcom_detail(user: User) -> DexcomConnectionDetail:
    """Build Dexcom connection detail from user model."""
    if not user.dexcom_access_token:
        return DexcomConnectionDetail(
            connected=False,
            has_valid_token=False,
            expires_at=None,
            last_sync=user.last_glucose_sync,
        )

    is_expired = (
        user.dexcom_expires_at is not None
        and user.dexcom_expires_at < datetime.now(timezone.utc)
    )

    return DexcomConnectionDetail(
        connected=True,
        has_valid_token=not is_expired,
        expires_at=user.dexcom_expires_at,
        last_sync=user.last_glucose_sync,
    )


def _get_librelinkup_detail(user: User) -> LibreLinkUpConnectionDetail:
    """Build LibreLinkUp connection detail from user model."""
    if not user.librelinkup_email:
        return LibreLinkUpConnectionDetail(
            connected=False,
            email=None,
            region=None,
            last_sync=None,
        )

    return LibreLinkUpConnectionDetail(
        connected=user.librelinkup_connected,
        email=user.librelinkup_email,
        region=user.librelinkup_region or "EU2",
        last_sync=user.last_librelinkup_sync,
    )


def _get_nightscout_detail(user: User) -> NightscoutConnectionDetail:
    """Build Nightscout connection detail from user model."""
    if not user.nightscout_url:
        return NightscoutConnectionDetail(
            connected=False,
            url=None,
            has_token=False,
            last_sync=None,
        )

    return NightscoutConnectionDetail(
        connected=user.nightscout_connected,
        url=user.nightscout_url,
        has_token=bool(user.nightscout_api_token),
        last_sync=user.last_nightscout_sync,
    )


# ── Endpoints ──


@route.get("/cgm/status", response_model=CGMConnectionStatus)
async def get_cgm_status(
    user: User = Depends(require_active_user),
) -> CGMConnectionStatus:
    """Get consolidated CGM connection status.

    Returns the current connection state for Nightscout, Dexcom, and LibreLinkUp,
    so the frontend can show a unified devices/sources screen.
    Nightscout is the recommended source for most users (vendor-agnostic, no legal risk).
    """
    dexcom = _get_dexcom_detail(user)
    nightscout = _get_nightscout_detail(user)
    librelinkup = _get_librelinkup_detail(user)

    # Most recent sync across all sources
    syncs = [user.last_glucose_sync, user.last_nightscout_sync, user.last_librelinkup_sync]
    last_sync = max((s for s in syncs if s is not None), default=None)

    # Contextual recommendation: Dexcom users have an official API alternative,
    # but Nightscout is the universal recommendation
    if dexcom.connected:
        recommended = "dexcom"
    elif nightscout.connected:
        recommended = "nightscout"
    elif librelinkup.connected:
        recommended = "nightscout"  # LibreLinkUp users should move to Nightscout
    else:
        recommended = "nightscout"

    return CGMConnectionStatus(
        nightscout=nightscout,
        dexcom=dexcom,
        librelinkup=librelinkup,
        any_connected=dexcom.connected or nightscout.connected or librelinkup.connected,
        last_sync=last_sync,
        recommended_source=recommended,
    )


@route.get("/cgm/dexcom/auth-url", response_model=DexcomAuthUrlResponse)
async def get_dexcom_auth_url(
    user: User = Depends(require_active_user),
) -> DexcomAuthUrlResponse:
    """Get Dexcom OAuth authorization URL.

    Returns the URL the frontend should redirect the user to for Dexcom OAuth.
    Generates a state token for CSRF protection.
    """
    from app.services.dexcom_service import DexcomService

    settings = get_settings()

    if not settings.DEXCOM_CLIENT_ID or "your-dexcom" in (settings.DEXCOM_CLIENT_ID or ""):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Dexcom integration is not configured. Set DEXCOM_CLIENT_ID in .env",
        )

    # Generate CSRF state token
    state = secrets.token_urlsafe(32)

    dexcom = DexcomService(
        client_id=settings.DEXCOM_CLIENT_ID,
        client_secret=settings.DEXCOM_CLIENT_SECRET,
        redirect_uri=settings.DEXCOM_REDIRECT_URI,
        use_sandbox=getattr(settings, "DEXCOM_USE_SANDBOX", False),
    )

    auth_url = dexcom.get_authorization_url(state)

    # In production, store state in user session or Redis for CSRF validation
    logger.info(f"Dexcom auth URL generated for user {user.id}, state={state[:8]}...")

    return DexcomAuthUrlResponse(
        auth_url=auth_url,
        state=state,
    )


@route.post("/cgm/dexcom/callback", response_model=CGMConnectResponse)
async def dexcom_callback(
    code: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> CGMConnectResponse:
    """Handle Dexcom OAuth callback.

    Exchange the authorization code for tokens and store them on the user.
    The frontend calls this after the Dexcom OAuth redirect.
    """
    from app.services.dexcom_service import DexcomService, DexcomServiceError

    settings = get_settings()

    try:
        dexcom = DexcomService(
            client_id=settings.DEXCOM_CLIENT_ID,
            client_secret=settings.DEXCOM_CLIENT_SECRET,
            redirect_uri=settings.DEXCOM_REDIRECT_URI,
            use_sandbox=getattr(settings, "DEXCOM_USE_SANDBOX", False),
        )

        tokens = await dexcom.exchange_code_for_tokens(code)

        # Store tokens on user
        user.dexcom_access_token = tokens.access_token
        user.dexcom_refresh_token = tokens.refresh_token
        user.dexcom_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)
        user.updated_at = datetime.now(timezone.utc)

        await session.commit()

        logger.info(f"Dexcom connected for user {user.id}, expires {user.dexcom_expires_at}")

        return CGMConnectResponse(
            success=True,
            message="Dexcom connected successfully",
            source="dexcom",
        )

    except DexcomServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dexcom callback failed: {str(e)}",
        )


@route.post("/cgm/dexcom/disconnect", response_model=CGMConnectResponse)
async def dexcom_disconnect(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> CGMConnectResponse:
    """Disconnect Dexcom.

    Removes stored OAuth tokens so data sync stops.
    """
    user.dexcom_access_token = None
    user.dexcom_refresh_token = None
    user.dexcom_expires_at = None
    user.updated_at = datetime.now(timezone.utc)

    await session.commit()

    logger.info(f"Dexcom disconnected for user {user.id}")

    return CGMConnectResponse(
        success=True,
        message="Dexcom disconnected",
        source="dexcom",
    )


@route.post("/cgm/nightscout/connect", response_model=CGMConnectResponse)
async def nightscout_connect(
    connect_data: NightscoutConnectRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> CGMConnectResponse:
    """Connect Nightscout instance.

    Store the Nightscout URL and optional API token, then test the connection.
    Returns success only if the connection test passes.
    """
    from app.services.nightscout_service import NightscoutService, NightscoutServiceError

    url = connect_data.url.rstrip("/")
    api_token = connect_data.api_token or None

    # Test the connection before saving
    service = NightscoutService(base_url=url, api_token=api_token)
    try:
        await service._test_connection()
    except NightscoutServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nightscout connection failed: {str(e)}",
        )

    # Also try fetching a reading to confirm data flows
    try:
        latest = await service.get_latest_glucose()
        readings_ok = latest is not None
    except NightscoutServiceError:
        readings_ok = False

    # Save to user
    user.nightscout_url = url
    user.nightscout_api_token = api_token
    user.nightscout_connected = True
    user.updated_at = datetime.now(timezone.utc)

    await session.commit()

    logger.info(
        f"Nightscout connected for user {user.id}, url={url}, "
        f"readings_ok={readings_ok}"
    )

    return CGMConnectResponse(
        success=True,
        message=(
            "Nightscout connected successfully"
            if readings_ok
            else "Nightscout connected, but no recent glucose readings found"
        ),
        source="nightscout",
    )


@route.post("/cgm/nightscout/disconnect", response_model=CGMConnectResponse)
async def nightscout_disconnect(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> CGMConnectResponse:
    """Disconnect Nightscout.

    Removes the stored Nightscout URL and token so data sync stops.
    """
    user.nightscout_url = None
    user.nightscout_api_token = None
    user.nightscout_connected = False
    user.last_nightscout_sync = None
    user.updated_at = datetime.now(timezone.utc)

    await session.commit()

    logger.info(f"Nightscout disconnected for user {user.id}")

    return CGMConnectResponse(
        success=True,
        message="Nightscout disconnected",
        source="nightscout",
    )


@route.post("/cgm/nightscout/test", response_model=NightscoutTestResult)
async def nightscout_test(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> NightscoutTestResult:
    """Test Nightscout connection.

    Test the currently stored Nightscout connection and return status.
    Useful for the frontend to verify everything is working.
    """
    from app.services.nightscout_service import NightscoutService, NightscoutServiceError

    if not user.nightscout_url:
        return NightscoutTestResult(
            success=False,
            message="No Nightscout URL configured",
            latest_reading=None,
            readings_24h=None,
        )

    service = NightscoutService(
        base_url=user.nightscout_url,
        api_token=user.nightscout_api_token,
    )

    try:
        # Test connection
        await service._test_connection()

        # Get latest reading
        latest = await service.get_latest_glucose()
        latest_dict = None
        if latest:
            ts = datetime.fromtimestamp(latest.date / 1000, tz=timezone.utc)
            latest_dict = {
                "sgv": latest.sgv,
                "direction": latest.direction or "unknown",
                "timestamp": ts.isoformat(),
                "device": latest.device or "unknown",
            }

        # Count readings in last 24h
        from datetime import timedelta
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=24)
        readings = await service.get_glucose_readings(start, end, max_count=1000)

        return NightscoutTestResult(
            success=True,
            message=(
                f"Connected. {len(readings)} readings in 24h, "
                f"latest: {latest.sgv if latest else 'N/A'} mg/dL"
            ),
            latest_reading=latest_dict,
            readings_24h=len(readings),
        )

    except NightscoutServiceError as e:
        return NightscoutTestResult(
            success=False,
            message=f"Connection failed: {str(e)}",
            latest_reading=None,
            readings_24h=None,
        )


@route.post("/cgm/sync", response_model=dict)
async def trigger_cgm_sync(
    source: str | None = None,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Trigger a manual CGM data sync.

    Optionally specify a source ('dexcom', 'nightscout') or sync all connected sources.
    This will run in the background via Celery.
    """
    # Determine which sources to sync
    sources_to_sync = []

    if source and source in ("dexcom", "nightscout", "librelinkup"):
        sources_to_sync.append(source)
    else:
        if user.dexcom_access_token:
            sources_to_sync.append("dexcom")
        if user.nightscout_connected and user.nightscout_url:
            sources_to_sync.append("nightscout")
        if user.librelinkup_connected and user.librelinkup_email:
            sources_to_sync.append("librelinkup")

    if not sources_to_sync:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected CGM sources to sync. Connect Dexcom, Nightscout, or LibreLinkUp first.",
        )

    # Trigger sync (non-blocking via Celery)
    results = []
    for src in sources_to_sync:
        try:
            task_result = await trigger_manual_sync(user.id, source=src)
            results.append(task_result)
        except Exception as e:
            logger.error(f"Sync failed for {src}: {e}")
            results.append({"source": src, "error": str(e), "success": False})

    return {
        "status": "sync_triggered",
        "sources": sources_to_sync,
        "results": results,
    }


# ── LibreLinkUp Endpoints ──


@route.post("/cgm/librelinkup/connect", response_model=CGMConnectResponse)
async def librelinkup_connect(
    connect_data: LibreLinkUpConnectRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> CGMConnectResponse:
    """Connect LibreLinkUp account.

    Store LibreLinkUp credentials and test the connection.
    Returns success only if the connection test passes.
    """
    from app.services.librelinkup_service import LibreLinkUpService, LibreLinkUpServiceError

    email = connect_data.email.strip()
    password = connect_data.password
    region = connect_data.region.upper()

    # Test the connection before saving
    service = LibreLinkUpService(
        email=email,
        password=password,
        region=region,
    )
    try:
        await service.login()
        patient_name = None
        try:
            await service.get_patient_id()
        except LibreLinkUpServiceError:
            pass
    except LibreLinkUpServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LibreLinkUp connection failed: {str(e)}",
        )

    # Save to user
    user.librelinkup_email = email
    user.librelinkup_password = password
    user.librelinkup_region = region
    user.librelinkup_connected = True
    user.updated_at = datetime.now(timezone.utc)

    await session.commit()

    logger.info(f"LibreLinkUp connected for user {user.id}, email={email}, region={region}")

    return CGMConnectResponse(
        success=True,
        message="LibreLinkUp connected successfully",
        source="librelinkup",
    )


@route.post("/cgm/librelinkup/disconnect", response_model=CGMConnectResponse)
async def librelinkup_disconnect(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> CGMConnectResponse:
    """Disconnect LibreLinkUp.

    Removes stored LibreLinkUp credentials so data sync stops.
    """
    user.librelinkup_email = None
    user.librelinkup_password = None
    user.librelinkup_region = None
    user.librelinkup_connected = False
    user.last_librelinkup_sync = None
    user.updated_at = datetime.now(timezone.utc)

    await session.commit()

    logger.info(f"LibreLinkUp disconnected for user {user.id}")

    return CGMConnectResponse(
        success=True,
        message="LibreLinkUp disconnected",
        source="librelinkup",
    )


@route.get("/cgm/sources", response_model=list[CgmSourceInfo])
async def get_cgm_sources() -> list[CgmSourceInfo]:
    """List available CGM sources.

    Unified source list so the frontend can render a single
    "Connect CGM" screen without knowing about backends.
    """
    from app.services.cgm_bridge_service import CgmBridgeService

    service = CgmBridgeService(None)
    raw = await service.get_available_sources()
    return [CgmSourceInfo(**s) for s in raw]


@route.post("/cgm/connect", response_model=CGMConnectResponse)
async def cgm_connect(
    req: CgmConnectRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> CGMConnectResponse:
    """Unified CGM connection endpoint.

    Single endpoint for connecting any CGM source:
    - Dexcom → returns auth URL
    - LibreLinkUp → enter email/password (+ consent)
    - Nightscout → enter URL + token

    The frontend calls this instead of three separate endpoints.
    """
    from app.services.cgm_bridge_service import CgmBridgeService, CgmSource

    # Validate consent for LibreLinkUp
    if req.source == "librelinkup" and not req.consent_given:
        return CGMConnectResponse(
            success=False,
            message="Please accept the disclaimer to use LibreLinkUp.",
            source="librelinkup",
        )

    source = CgmSource(req.source)
    service = CgmBridgeService(session)

    if source == CgmSource.DEXCOM:
        # Redirect to Dexcom OAuth
        from app.config import get_settings
        settings = get_settings()
        if not settings.dexcom_client_id:
            return CGMConnectResponse(
                success=False,
                message="Dexcom integration not configured.",
                source="dexcom",
            )
        return CGMConnectResponse(
            success=True,
            message="dexcom_auth_required",  # frontend should redirect
            source="dexcom",
        )

    elif source == CgmSource.LIBRELINKUP:
        if not req.email or not req.password:
            return CGMConnectResponse(
                success=False,
                message="Email and password required.",
                source="librelinkup",
            )
        # Test connection via bridge
        result = await service.connect(
            CgmSource.LIBRELINKUP,
            user.id,
            librelinkup_email=req.email,
            librelinkup_password=req.password,
            librelinkup_region=req.region,
        )
        if result.success:
            # Store credentials
            user.librelinkup_email = req.email
            user.librelinkup_password = req.password
            user.librelinkup_region = req.region
            user.updated_at = datetime.now(timezone.utc)
            await session.commit()
            return CGMConnectResponse(
                success=True,
                message="LibreLinkUp connected successfully.",
                source="librelinkup",
            )
        return CGMConnectResponse(
            success=False,
            message=result.message,
            source="librelinkup",
        )

    elif source == CgmSource.NIGHTSCOUT:
        if not req.url:
            return CGMConnectResponse(
                success=False,
                message="Nightscout URL required.",
                source="nightscout",
            )
        user.nightscout_url = req.url
        user.nightscout_api_token = req.api_token
        user.updated_at = datetime.now(timezone.utc)
        await session.commit()
        return CGMConnectResponse(
            success=True,
            message="Nightscout connected.",
            source="nightscout",
        )

    return CGMConnectResponse(
        success=False,
        message=f"Unknown source: {req.source}",
        source="unknown",
    )


@route.post("/cgm/librelinkup/test", response_model=LibreLinkUpTestResult)
async def librelinkup_test(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> LibreLinkUpTestResult:
    """Test LibreLinkUp connection.

    Test the currently stored LibreLinkUp connection and return status.
    """
    from app.services.librelinkup_service import LibreLinkUpService, LibreLinkUpServiceError

    if not user.librelinkup_email:
        return LibreLinkUpTestResult(
            success=False,
            message="No LibreLinkUp account configured",
            patient_name=None,
            latest_value=None,
            latest_trend=None,
            readings_count=None,
        )

    service = LibreLinkUpService(
        email=user.librelinkup_email,
        password=user.librelinkup_password,
        region=user.librelinkup_region or "EU2",
    )

    try:
        # Login
        await service.login()

        # Get patient info
        await service.get_patient_id()

        # Get readings
        readings = await service.get_glucose_readings(max_count=500)

        latest = readings[0] if readings else None

        return LibreLinkUpTestResult(
            success=True,
            message=(
                f"Connected. {len(readings)} readings found, "
                f"latest: {latest.value_mg_dl if latest else 'N/A'} mg/dL"
            ),
            patient_name="Tom Batchelor",  # Could fetch dynamically
            latest_value=latest.value_mg_dl if latest else None,
            latest_trend=service._trend_arrow_to_description(latest.trend_arrow) if latest else None,
            readings_count=len(readings),
        )

    except LibreLinkUpServiceError as e:
        return LibreLinkUpTestResult(
            success=False,
            message=f"Connection failed: {str(e)}",
            patient_name=None,
            latest_value=None,
            latest_trend=None,
            readings_count=None,
        )