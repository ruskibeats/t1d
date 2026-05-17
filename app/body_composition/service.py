from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from app.body_composition.models import BodyCompositionEntry
from app.body_composition.schemas import BodyCompositionEntryCreate
from app.metrics.types import MetricType
from app.services.metric_writer import write_metric_if_present


class BodyCompositionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: BodyCompositionEntryCreate) -> BodyCompositionEntry:
        entry = BodyCompositionEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        await write_metric_if_present(self.db, user_id, MetricType.WEIGHT, entry.weight_kg, "kg", entry.measured_at, entry.source)
        await write_metric_if_present(self.db, user_id, MetricType.BODY_FAT_PERCENT, entry.body_fat_percent, "%", entry.measured_at, entry.source)
        await write_metric_if_present(self.db, user_id, MetricType.BMI, entry.bmi, "kg/m2", entry.measured_at, entry.source)
        await write_metric_if_present(self.db, user_id, MetricType.LEAN_MASS, entry.lean_mass_kg, "kg", entry.measured_at, entry.source)
        await write_metric_if_present(self.db, user_id, MetricType.WAIST_CIRCUMFERENCE, entry.waist_cm, "cm", entry.measured_at, entry.source)
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[BodyCompositionEntry]:
        result = await self.db.execute(
            select(BodyCompositionEntry).where(BodyCompositionEntry.user_id == user_id, BodyCompositionEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list(self, user_id: int, start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None, limit: int = 100, offset: int = 0) -> List[BodyCompositionEntry]:
        stmt = select(BodyCompositionEntry).where(BodyCompositionEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(BodyCompositionEntry.measured_at >= start_date)
        if end_date:
            stmt = stmt.where(BodyCompositionEntry.measured_at <= end_date)
        stmt = stmt.order_by(desc(BodyCompositionEntry.measured_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, user_id: int, entry_id: int) -> bool:
        entry = await self.get(user_id, entry_id)
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True
