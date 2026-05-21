from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from app.lifestyle.models import LifestyleEntry
from app.lifestyle.schemas import LifestyleEntryCreate
from app.metrics.types import MetricType
from app.services.metric_registry import MetricRegistry


class LifestyleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._metric_registry = MetricRegistry(db)

    async def create(self, user_id: int, data: LifestyleEntryCreate) -> LifestyleEntry:
        entry = LifestyleEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        await self._metric_registry.record_metrics_batch(
            user_id=user_id,
            measured_at=entry.measured_at,
            source=entry.source,
            metrics=[
                {"metric_type": MetricType.STRESS_LEVEL, "value": entry.stress_level, "unit": "score"},
                {"metric_type": MetricType.ENERGY_LEVEL, "value": entry.energy_level, "unit": "score"},
                {"metric_type": MetricType.CAFFEINE, "value": entry.caffeine_mg, "unit": "mg"},
            ]
        )
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[LifestyleEntry]:
        result = await self.db.execute(
            select(LifestyleEntry).where(LifestyleEntry.user_id == user_id, LifestyleEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list(self, user_id: int, start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None, limit: int = 100, offset: int = 0) -> List[LifestyleEntry]:
        stmt = select(LifestyleEntry).where(LifestyleEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(LifestyleEntry.measured_at >= start_date)
        if end_date:
            stmt = stmt.where(LifestyleEntry.measured_at <= end_date)
        stmt = stmt.order_by(desc(LifestyleEntry.measured_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, user_id: int, entry_id: int) -> bool:
        entry = await self.get(user_id, entry_id)
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True
