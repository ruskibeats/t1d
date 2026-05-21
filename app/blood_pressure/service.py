from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from app.blood_pressure.models import BloodPressureEntry
from app.blood_pressure.schemas import BloodPressureEntryCreate
from app.metrics.types import MetricType
from app.services.metric_registry import MetricRegistry


class BloodPressureService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._metric_registry = MetricRegistry(db)

    async def create(self, user_id: int, data: BloodPressureEntryCreate) -> BloodPressureEntry:
        entry = BloodPressureEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        await self._metric_registry.record_metrics_batch(
            user_id=user_id,
            measured_at=entry.measured_at,
            source=entry.source,
            metrics=[
                {"metric_type": MetricType.BLOOD_PRESSURE_SYSTOLIC, "value": entry.systolic, "unit": "mmHg"},
                {"metric_type": MetricType.BLOOD_PRESSURE_DIASTOLIC, "value": entry.diastolic, "unit": "mmHg"},
            ]
        )
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[BloodPressureEntry]:
        result = await self.db.execute(
            select(BloodPressureEntry).where(BloodPressureEntry.user_id == user_id, BloodPressureEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list(self, user_id: int, start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None, limit: int = 100, offset: int = 0) -> List[BloodPressureEntry]:
        stmt = select(BloodPressureEntry).where(BloodPressureEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(BloodPressureEntry.measured_at >= start_date)
        if end_date:
            stmt = stmt.where(BloodPressureEntry.measured_at <= end_date)
        stmt = stmt.order_by(desc(BloodPressureEntry.measured_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, user_id: int, entry_id: int) -> bool:
        entry = await self.get(user_id, entry_id)
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True
