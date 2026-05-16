"""FastAPI routes for Withings webhook and data sync."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.metrics.schemas import BatchHealthMetricCreate
from app.metrics.service import HealthMetricService

route = APIRouter(prefix="/withings", tags=["Withings"])


@route.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def withings_webhook(
    payload: dict,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Receive Withings notification webhook."""
    from app.ingestion.withings import WithingsIngestionService
    ingestion = WithingsIngestionService()
    metrics = ingestion.handle_notification(payload)
    if metrics:
        metric_service = HealthMetricService(db)
        batch = BatchHealthMetricCreate(metrics=metrics)
        await metric_service.create_batch(user_id, batch)
    return {"status": "accepted", "processed": len(metrics)}
