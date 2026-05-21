from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mood.models import MoodEntry
from app.mood.schemas import MoodEntryCreate
from app.metrics.types import MetricType
from app.services.metric_registry import MetricRegistry


class MoodService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._metric_registry = MetricRegistry(db)

    async def create(self, user_id: int, data: MoodEntryCreate) -> MoodEntry:
        entry = MoodEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        await self._metric_registry.record_metric(
            user_id=user_id,
            metric_type=MetricType.MOOD_SCORE,
            value=entry.score,
            measured_at=entry.logged_at,
            unit="score",
            source=entry.source,
        )
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[MoodEntry]:
        result = await self.db.execute(
            select(MoodEntry).where(MoodEntry.user_id == user_id, MoodEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ):
        stmt = select(MoodEntry).where(MoodEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(MoodEntry.logged_at >= start_date)
        if end_date:
            stmt = stmt.where(MoodEntry.logged_at <= end_date)
        stmt = stmt.order_by(desc(MoodEntry.logged_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, user_id: int, entry_id: int, data: MoodEntryCreate
    ) -> Optional[MoodEntry]:
        entry = await self.get(user_id, entry_id)
        if not entry:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entry, field, value)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def delete(self, user_id: int, entry_id: int) -> bool:
        entry = await self.get(user_id, entry_id)
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True

    async def get_mood_stats(self, user_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """Get mood statistics over a time period."""
        stmt = select(MoodEntry).where(MoodEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(MoodEntry.logged_at >= start_date)
        if end_date:
            stmt = stmt.where(MoodEntry.logged_at <= end_date)
        
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())
        
        if not entries:
            return None
            
        scores = [e.score for e in entries]
        return {
            "count": len(entries),
            "min_score": min(scores),
            "max_score": max(scores),
            "avg_score": sum(scores) / len(scores),
            "start_date": min(e.logged_at for e in entries),
            "end_date": max(e.logged_at for e in entries),
        }