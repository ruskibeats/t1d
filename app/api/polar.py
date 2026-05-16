"""FastAPI routes for Polar data sync."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

route = APIRouter(prefix="/polar", tags=["Polar"])


@route.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def polar_sync(
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a Polar data sync. Requires stored OAuth tokens."""
    return {
        "status": "sync_initiated",
        "message": "Polar sync requires stored OAuth tokens. Implement token storage in User model.",
    }
