"""Helpers for dual-writing domain entries into the unified health_metrics store."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics.schemas import HealthMetricCreate
from app.metrics.service import HealthMetricService
from app.metrics.types import MetricType


async def write_metric_if_present(
    db: AsyncSession,
    user_id: int,
    metric_type: MetricType,
    value: float | int | None,
    unit: str,
    measured_at: datetime,
    source: str = "manual",
    meta: dict[str, Any] | None = None,
) -> None:
    """Write a health metric when the source value exists.

    Domain-specific tables remain the operational source for CRUD while this
    creates the unified graph/analytics fact row.
    """
    if value is None:
        return
    if value < 0:
        return
    await HealthMetricService(db).create(
        user_id,
        HealthMetricCreate(
            type=metric_type,
            value=float(value),
            unit=unit,
            measured_at=measured_at,
            source=source,
            meta=meta,
        ),
    )
