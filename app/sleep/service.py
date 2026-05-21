from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, and_, func
from typing import List, Optional

from app.sleep.models import SleepEntry, SleepStage
from app.sleep.schemas import SleepEntryCreate, SleepStageCreate
from app.metrics.types import MetricType
from app.services.metric_registry import MetricRegistry


class SleepService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._metric_registry = MetricRegistry(db)

    async def create(self, user_id: int, data: SleepEntryCreate) -> SleepEntry:
        entry = SleepEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        # Dual-write via consolidated registry (batch metrics)
        duration_hours = (entry.duration_minutes / 60) if entry.duration_minutes else None
        await self._metric_registry.record_metrics_batch(
            user_id=user_id,
            measured_at=entry.start_time,
            source=entry.source,
            metrics=[
                {"metric_type": MetricType.SLEEP_HOURS, "value": duration_hours, "unit": "hours"},
                {"metric_type": MetricType.SLEEP_SCORE, "value": entry.quality_score, "unit": "score"},
                {"metric_type": MetricType.SLEEP_DEEP, "value": entry.deep_minutes, "unit": "minutes"},
                {"metric_type": MetricType.SLEEP_LIGHT, "value": entry.light_minutes, "unit": "minutes"},
                {"metric_type": MetricType.SLEEP_REM, "value": entry.rem_minutes, "unit": "minutes"},
                {"metric_type": MetricType.SLEEP_AWAKE, "value": entry.awake_minutes, "unit": "minutes"},
            ]
        )
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[SleepEntry]:
        result = await self.db.execute(
            select(SleepEntry).where(SleepEntry.user_id == user_id, SleepEntry.id == entry_id)
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
        stmt = select(SleepEntry).where(SleepEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(SleepEntry.start_time >= start_date)
        if end_date:
            stmt = stmt.where(SleepEntry.start_time <= end_date)
        stmt = stmt.order_by(desc(SleepEntry.start_time)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_stage(self, entry_id: int, data: SleepStageCreate) -> SleepStage:
        # Verify entry exists and belongs to user (caller should ensure)
        stage = SleepStage(entry_id=entry_id, **data.model_dump())
        self.db.add(stage)
        await self.db.flush()
        await self.db.refresh(stage)
        return stage

    async def list_stages_for_entry(self, entry_id: int) -> List[SleepStage]:
        result = await self.db.execute(
            select(SleepStage)
            .where(SleepStage.entry_id == entry_id)
            .order_by(SleepStage.start_time)
        )
        return list(result.scalars().all())

    async def update(
        self, user_id: int, entry_id: int, data: SleepEntryCreate
    ) -> Optional[SleepEntry]:
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