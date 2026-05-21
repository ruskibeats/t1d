from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from app.body_composition.models import BodyCompositionEntry
from app.body_composition.schemas import BodyCompositionEntryCreate
from app.metrics.types import MetricType
from app.services.metric_registry import MetricRegistry


class BodyCompositionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._metric_registry = MetricRegistry(db)

    async def create(self, user_id: int, data: BodyCompositionEntryCreate) -> BodyCompositionEntry:
        entry = BodyCompositionEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        # Dual-write via consolidated registry (batch metrics)
        await self._metric_registry.record_metrics_batch(
            user_id=user_id,
            measured_at=entry.measured_at,
            source=entry.source,
            metrics=[
                {"metric_type": MetricType.WEIGHT, "value": entry.weight_kg, "unit": "kg"},
                {"metric_type": MetricType.BODY_FAT_PERCENT, "value": entry.body_fat_percent, "unit": "%"},
                {"metric_type": MetricType.BMI, "value": entry.bmi, "unit": "kg/m2"},
                {"metric_type": MetricType.LEAN_MASS, "value": entry.lean_mass_kg, "unit": "kg"},
                {"metric_type": MetricType.WAIST_CIRCUMFERENCE, "value": entry.waist_cm, "unit": "cm"},
            ]
        )
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
