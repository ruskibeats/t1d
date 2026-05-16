"""Garmin webhook and sync endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.ingestion.garmin import GarminIngestionService
from app.metrics.service import HealthMetricService

route = APIRouter(prefix="/garmin", tags=["garmin"])


@route.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def garmin_webhook(
    payload: dict,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Receive Garmin webhook data.

    Processes activities, sleep, and body composition data
    pushed from Garmin Connect.
    """
    metric_service = HealthMetricService(db)
    ingestion_service = GarminIngestionService(metric_service)

    try:
        counts = await ingestion_service.ingest_webhook(user_id, payload)
        return {"status": "accepted", "counts": counts}
    except Exception as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Failed to process Garmin data: {str(e)}",
        )


@route.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_garmin(
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a sync with Garmin Connect.

    Note: This endpoint initiates the sync process. Actual data
    retrieval requires Garmin API credentials and OAuth flow.
    """
    return {"status": "sync_initiated", "message": "Connect your Garmin account in settings"}