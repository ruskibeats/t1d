from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from app.activity.models import ActivityEntry
from app.activity.schemas import ActivityEntryCreate
from app.metrics.types import MetricType
from app.services.metric_writer import write_metric_if_present


class ActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: ActivityEntryCreate) -> ActivityEntry:
        entry = ActivityEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        await write_metric_if_present(self.db, user_id, MetricType.STEPS, entry.steps, "steps", entry.measured_at, entry.source)
        await write_metric_if_present(self.db, user_id, MetricType.DISTANCE_KM, entry.distance_km, "km", entry.measured_at, entry.source)
        await write_metric_if_present(self.db, user_id, MetricType.FLOORS_CLIMBED, entry.floors_climbed, "floors", entry.measured_at, entry.source)
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[ActivityEntry]:
        result = await self.db.execute(
            select(ActivityEntry).where(ActivityEntry.user_id == user_id, ActivityEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list(self, user_id: int, start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None, limit: int = 100, offset: int = 0) -> List[ActivityEntry]:
        stmt = select(ActivityEntry).where(ActivityEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(ActivityEntry.measured_at >= start_date)
        if end_date:
            stmt = stmt.where(ActivityEntry.measured_at <= end_date)
        stmt = stmt.order_by(desc(ActivityEntry.measured_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, user_id: int, entry_id: int) -> bool:
        entry = await self.get(user_id, entry_id)
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True
