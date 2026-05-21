from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, and_, func
from typing import List, Optional

from app.exercise.models import ExerciseEntry, ExerciseEntrySet
from app.exercise.schemas import ExerciseEntryCreate, ExerciseEntrySetCreate
from app.metrics.types import MetricType
from app.services.metric_registry import MetricRegistry


class ExerciseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._metric_registry = MetricRegistry(db)

    async def create(self, user_id: int, data: ExerciseEntryCreate) -> ExerciseEntry:
        entry = ExerciseEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        # Dual-write via consolidated registry
        await self._metric_registry.record_metric(
            user_id=user_id,
            metric_type=MetricType.EXERCISE_MINUTES,
            value=entry.duration_minutes,
            measured_at=entry.start_time,
            unit="minutes",
            source=entry.source,
        )
        await self._metric_registry.record_metric(
            user_id=user_id,
            metric_type=MetricType.EXERCISE_CALORIES,
            value=entry.calories,
            measured_at=entry.start_time,
            unit="kcal",
            source=entry.source,
        )
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[ExerciseEntry]:
        result = await self.db.execute(
            select(ExerciseEntry).where(ExerciseEntry.user_id == user_id, ExerciseEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exercise_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ):
        stmt = select(ExerciseEntry).where(ExerciseEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(ExerciseEntry.start_time >= start_date)
        if end_date:
            stmt = stmt.where(ExerciseEntry.start_time <= end_date)
        if exercise_type:
            stmt = stmt.where(ExerciseEntry.type == exercise_type)
        stmt = stmt.order_by(desc(ExerciseEntry.start_time)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_set(self, entry_id: int, data: ExerciseEntrySetCreate) -> ExerciseEntrySet:
        # Verify entry exists and belongs to user (caller should ensure)
        entry_set = ExerciseEntrySet(entry_id=entry_id, **data.model_dump())
        self.db.add(entry_set)
        await self.db.flush()
        await self.db.refresh(entry_set)
        return entry_set

    async def list_sets_for_entry(self, entry_id: int) -> List[ExerciseEntrySet]:
        result = await self.db.execute(
            select(ExerciseEntrySet)
            .where(ExerciseEntrySet.entry_id == entry_id)
            .order_by(ExerciseEntrySet.set_number)
        )
        return list(result.scalars().all())

    async def update(
        self, user_id: int, entry_id: int, data: ExerciseEntryCreate
    ) -> Optional[ExerciseEntry]:
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