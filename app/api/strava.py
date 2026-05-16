"""FastAPI routes for Strava OAuth and data sync."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

route = APIRouter(prefix="/strava", tags=["Strava"])


@route.get("/auth")
async def strava_auth_url(client_id: str = Query(...), redirect_uri: str = Query(...)):
    """Get Strava OAuth authorization URL."""
    from app.ingestion.strava import StravaIngestionService
    url = StravaIngestionService.authorize_url(client_id, redirect_uri)
    return {"authorization_url": url}


@route.get("/callback")
async def strava_callback(code: str = Query(...)):
    """Handle Strava OAuth callback (token exchange placeholder)."""
    return {
        "status": "authorized",
        "message": "Exchange the code for tokens server-side using client_id and client_secret",
        "code": code[:10] + "...",
    }


@route.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def strava_sync(
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a Strava data sync. Requires stored OAuth tokens."""
    return {
        "status": "sync_initiated",
        "message": "Strava sync requires stored OAuth tokens. Implement token storage in User model.",
    }
