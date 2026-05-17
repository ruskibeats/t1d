from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from app.vitals.models import VitalEntry
from app.vitals.schemas import VitalEntryCreate
from app.metrics.types import MetricType
from app.services.metric_writer import write_metric_if_present


class VitalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: VitalEntryCreate) -> VitalEntry:
        entry = VitalEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        await write_metric_if_present(self.db, user_id, MetricType.SPO2, entry.spo2_percent, "%", entry.measured_at, entry.source)
        await write_metric_if_present(self.db, user_id, MetricType.RESPIRATORY_RATE, entry.respiratory_rate, "breaths/min", entry.measured_at, entry.source)
        await write_metric_if_present(self.db, user_id, MetricType.TEMPERATURE, entry.body_temperature_c, "celsius", entry.measured_at, entry.source)
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[VitalEntry]:
        result = await self.db.execute(
            select(VitalEntry).where(VitalEntry.user_id == user_id, VitalEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list(self, user_id: int, start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None, limit: int = 100, offset: int = 0) -> List[VitalEntry]:
        stmt = select(VitalEntry).where(VitalEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(VitalEntry.measured_at >= start_date)
        if end_date:
            stmt = stmt.where(VitalEntry.measured_at <= end_date)
        stmt = stmt.order_by(desc(VitalEntry.measured_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, user_id: int, entry_id: int) -> bool:
        entry = await self.get(user_id, entry_id)
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True
