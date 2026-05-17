from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.fasting.models import FastingEntry
from app.fasting.schemas import FastingEntryCreate
from app.metrics.types import MetricType
from app.services.metric_writer import write_metric_if_present


class FastingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_entry(self, user_id: int, data: FastingEntryCreate) -> FastingEntry:
        entry = FastingEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        await write_metric_if_present(self.db, user_id, MetricType.FASTING_DURATION, entry.duration_minutes, "minutes", entry.start_time, entry.source)
        return entry

    async def get_entry(self, user_id: int, entry_id: int) -> Optional[FastingEntry]:
        result = await self.db.execute(
            select(FastingEntry).where(FastingEntry.user_id == user_id, FastingEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list_entries(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ):
        stmt = select(FastingEntry).where(FastingEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(FastingEntry.start_time >= start_date)
        if end_date:
            stmt = stmt.where(FastingEntry.start_time <= end_date)
        stmt = stmt.order_by(desc(FastingEntry.start_time)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_entry(
        self, user_id: int, entry_id: int, data: FastingEntryCreate
    ) -> Optional[FastingEntry]:
        entry = await self.get_entry(user_id, entry_id)
        if not entry:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entry, field, value)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def delete_entry(self, user_id: int, entry_id: int) -> bool:
        entry = await self.get_entry(user_id, entry_id)
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True

    async def get_active_fast(self, user_id: int) -> Optional[FastingEntry]:
        """Get currently active fasting entry (end_time is None)."""
        result = await self.db.execute(
            select(FastingEntry).where(
                FastingEntry.user_id == user_id, 
                FastingEntry.end_time.is_(None)
            ).order_by(FastingEntry.start_time.desc())
        )
        return result.scalar_one_or_none()

    async def calculate_duration(self, entry: FastingEntry) -> int:
        """Calculate fasting duration in minutes from start_time to end_time or now."""
        end_time = entry.end_time or datetime.now(entry.start_time.tzinfo)
        return int((end_time - entry.start_time).total_seconds() / 60)