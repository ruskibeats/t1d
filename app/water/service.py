"""Service layer for water tracking domain."""

from datetime import datetime
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.water.models import WaterEntry
from app.water.schemas import WaterEntryCreate
from app.metrics.types import MetricType
from app.services.metric_writer import write_metric_if_present


class WaterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: WaterEntryCreate) -> WaterEntry:
        model = WaterEntry(user_id=user_id, **data.model_dump())
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        await write_metric_if_present(self.db, user_id, MetricType.WATER, model.amount_ml, "ml", model.logged_at, model.source)
        return model

    async def list(
        self,
        user_id: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ):
        stmt = select(WaterEntry).where(WaterEntry.user_id == user_id)
        if start:
            stmt = stmt.where(WaterEntry.logged_at >= start)
        if end:
            stmt = stmt.where(WaterEntry.logged_at <= end)
        stmt = stmt.order_by(desc(WaterEntry.logged_at)).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, user_id: int, entry_id: int) -> bool:
        result = await self.db.execute(
            select(WaterEntry).where(WaterEntry.user_id == user_id, WaterEntry.id == entry_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self.db.delete(model)
        await self.db.flush()
        return True
