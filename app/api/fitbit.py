"""FastAPI routes for Fitbit OAuth and data sync."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.metrics.service import HealthMetricService

route = APIRouter(prefix="/fitbit", tags=["Fitbit"])


@route.get("/auth")
async def fitbit_auth_url(client_id: str = Query(...), redirect_uri: str = Query(...)):
    """Get Fitbit OAuth authorization URL."""
    from app.ingestion.fitbit import FitbitIngestionService
    url = FitbitIngestionService.authorize_url(client_id, redirect_uri)
    return {"authorization_url": url}


@route.get("/callback")
async def fitbit_callback(code: str = Query(...)):
    """Handle Fitbit OAuth callback (token exchange placeholder)."""
    return {
        "status": "authorized",
        "message": "Exchange the code for tokens server-side using client_id and client_secret",
        "code": code[:10] + "...",
    }


@route.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def fitbit_sync(
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a Fitbit data sync. Requires stored OAuth tokens."""
    return {
        "status": "sync_initiated",
        "message": "Fitbit sync requires stored OAuth tokens. Implement token storage in User model.",
    }
