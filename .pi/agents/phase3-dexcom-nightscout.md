---
name: phase3-dexcom-nightscout
description: Implements the Dexcom OAuth callback flow and Nightscout configuration API for the T1D Companion. Adds auth routes for Dexcom connection and Nightscout setup. Use when implementing Phase 3 data ingestion.
model: tencent/hy3-preview:free
context: fork
---

# Phase 3: Dexcom OAuth + Nightscout Integration

## Task

Implement the missing pieces for CGM data ingestion:
1. **Dexcom OAuth callback** — handle the OAuth redirect, exchange code for tokens, store in User model
2. **Nightscout configuration** — API routes for users to configure their Nightscout URL/credentials
3. **Connection status endpoints** — check if Dexcom/Nightscout are connected

## Files to Modify

- `app/api/auth.py` — add Dexcom OAuth callback endpoint
- `app/api/users.py` — add Nightscout configuration endpoints
- `app/db/models.py` — add Nightscout credential fields to User model (if needed)

## Part 1: Dexcom OAuth Callback

### Add to `app/api/auth.py`

```python
@router.get("/dexcom/callback")
async def dexcom_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    """Handle Dexcom OAuth2 callback.
    
    Exchanges the authorization code for access/refresh tokens
    and stores them in the user's profile.
    """
    from app.services.dexcom_service import DexcomService
    from app.config import get_settings
    
    settings = get_settings()
    
    if not settings.dexcom_client_id or not settings.dexcom_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Dexcom integration is not configured on this server.",
        )
    
    dexcom_service = DexcomService(
        client_id=settings.dexcom_client_id,
        client_secret=settings.dexcom_client_secret,
        redirect_uri=settings.dexcom_redirect_uri,
    )
    
    try:
        tokens = await dexcom_service.exchange_code_for_tokens(code)
        
        # Store tokens in user model
        user.dexcom_access_token = tokens.access_token
        user.dexcom_refresh_token = tokens.refresh_token
        from datetime import datetime, timezone, timedelta
        user.dexcom_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)
        
        await session.commit()
        
        return {
            "status": "connected",
            "message": "Dexcom account connected successfully.",
            "expires_at": user.dexcom_expires_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect Dexcom: {str(e)}",
        )


@router.get("/dexcom/status")
async def dexcom_status(
    user: User = Depends(require_active_user),
):
    """Check Dexcom connection status."""
    from datetime import datetime, timezone
    
    is_connected = bool(user.dexcom_access_token)
    is_expired = False
    
    if user.dexcom_expires_at:
        is_expired = user.dexcom_expires_at < datetime.now(timezone.utc)
    
    return {
        "connected": is_connected,
        "expired": is_expired,
        "expires_at": user.dexcom_expires_at.isoformat() if user.dexcom_expires_at else None,
    }


@router.post("/dexcom/disconnect")
async def dexcom_disconnect(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    """Disconnect Dexcom by clearing stored tokens."""
    user.dexcom_access_token = None
    user.dexcom_refresh_token = None
    user.dexcom_expires_at = None
    await session.commit()
    
    return {"status": "disconnected", "message": "Dexcom account disconnected."}


@router.post("/dexcom/refresh")
async def dexcom_refresh(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    """Refresh Dexcom access token using stored refresh token."""
    from app.services.dexcom_service import DexcomService
    from app.config import get_settings
    from datetime import datetime, timezone, timedelta
    
    if not user.dexcom_refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available.")
    
    settings = get_settings()
    dexcom_service = DexcomService(
        client_id=settings.dexcom_client_id,
        client_secret=settings.dexcom_client_secret,
        redirect_uri=settings.dexcom_redirect_uri,
    )
    
    try:
        tokens = await dexcom_service.refresh_access_token(user.dexcom_refresh_token)
        user.dexcom_access_token = tokens.access_token
        user.dexcom_refresh_token = tokens.refresh_token
        user.dexcom_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)
        await session.commit()
        
        return {
            "status": "refreshed",
            "expires_at": user.dexcom_expires_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token refresh failed: {str(e)}")
```

### Add Dexcom Service Import to `app/api/auth.py`

At the top of the file, add:
```python
from fastapi import Query
```

## Part 2: Nightscout Configuration

### Add Nightscout Fields to User Model

In `app/db/models.py`, add to the `User` class:

```python
# Nightscout configuration
nightscout_url: Mapped[str | None] = Column(String(512), nullable=True)
nightscout_api_token: Mapped[str | None] = Column(String(255), nullable=True)
nightscout_connected: Mapped[bool] = Column(Boolean, default=False, nullable=False)
last_nightscout_sync: Mapped[datetime | None] = Column(DateTime, nullable=True)
```

### Add Nightscout Endpoints to `app/api/users.py`

```python
from pydantic import BaseModel, HttpUrl

class NightscoutConfig(BaseModel):
    url: str = Field(..., description="Nightscout base URL")
    api_token: str | None = Field(None, description="Nightscout API token")

class NightscoutStatus(BaseModel):
    connected: bool
    url: str | None
    last_sync: str | None

@router.post("/me/nightscout")
async def configure_nightscout(
    config: NightscoutConfig,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    """Configure Nightscout connection for the current user."""
    from app.services.nightscout_service import NightscoutService
    
    # Validate the Nightscout URL
    nightscout_service = NightscoutService(
        base_url=config.url,
        api_token=config.api_token,
    )
    
    try:
        # Test the connection
        await nightscout_service._test_connection()
        
        # Store configuration
        user.nightscout_url = config.url
        user.nightscout_api_token = config.api_token
        user.nightscout_connected = True
        await session.commit()
        
        return {
            "status": "connected",
            "message": "Nightscout connected successfully.",
            "url": config.url,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to Nightscout: {str(e)}",
        )

@router.get("/me/nightscout", response_model=NightscoutStatus)
async def get_nightscout_status(
    user: User = Depends(require_active_user),
):
    """Get Nightscout connection status."""
    return NightscoutStatus(
        connected=user.nightscout_connected,
        url=user.nightscout_url,
        last_sync=user.last_nightscout_sync.isoformat() if user.last_nightscout_sync else None,
    )

@router.delete("/me/nightscout")
async def disconnect_nightscout(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    """Disconnect Nightscout."""
    user.nightscout_url = None
    user.nightscout_api_token = None
    user.nightscout_connected = False
    await session.commit()
    
    return {"status": "disconnected"}

@router.post("/me/nightscout/sync")
async def sync_nightscout(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    """Manually trigger a Nightscout sync."""
    from app.services.nightscout_service import NightscoutService
    from datetime import datetime, timezone
    
    if not user.nightscout_url:
        raise HTTPException(status_code=400, detail="Nightscout not configured.")
    
    nightscout_service = NightscoutService(
        base_url=user.nightscout_url,
        api_token=user.nightscout_api_token,
    )
    
    try:
        count = await nightscout_service.sync_glucose_data(session, user)
        user.last_nightscout_sync = datetime.now(timezone.utc)
        await session.commit()
        
        return {
            "status": "synced",
            "readings_imported": count,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sync failed: {str(e)}")
```

## Part 3: Alembic Migration

After modifying the User model, generate a migration:

```bash
alembic revision --autogenerate -m "add nightscout config to user"
alembic upgrade head
```

## Critical Rules

1. **Modify only:** `app/api/auth.py`, `app/api/users.py`, `app/db/models.py`
2. **Don't break existing auth routes** — add new ones, don't modify existing
3. **Validate Nightscout URL** — must be a valid HTTPS URL
4. **Test Nightscout connection before saving** — don't store invalid credentials
5. **Handle token expiration** — Dexcom tokens expire, refresh should be automatic
6. **Don't store plaintext passwords** — Nightscout API tokens are sensitive, consider encryption

## Verification

After writing, verify:
- [ ] Dexcom callback endpoint exists at `GET /auth/dexcom/callback`
- [ ] Dexcom status endpoint exists at `GET /auth/dexcom/status`
- [ ] Dexcom disconnect endpoint exists at `POST /auth/dexcom/disconnect`
- [ ] Dexcom refresh endpoint exists at `POST /auth/dexcom/refresh`
- [ ] Nightscout config endpoint exists at `POST /api/v1/users/me/nightscout`
- [ ] Nightscout status endpoint exists at `GET /api/v1/users/me/nightscout`
- [ ] Nightscout sync endpoint exists at `POST /api/v1/users/me/nightscout/sync`
- [ ] User model has Nightscout fields
- [ ] No import errors: `python -c "from app.api.auth import router; print('OK')"`
- [ ] No import errors: `python -c "from app.api.users import router; print('OK')"`

## Output

Write your implementation notes to: `PHASE3_W7_DEXCOM_NIGHTSCOUT.md`
