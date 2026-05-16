from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.measurements.models import CustomMeasurement
from app.measurements.schemas import CustomMeasurementCreate


class MeasurementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_measurement(self, user_id: int, data: CustomMeasurementCreate) -> CustomMeasurement:
        measurement = CustomMeasurement(user_id=user_id, **data.model_dump())
        self.db.add(measurement)
        await self.db.flush()
        await self.db.refresh(measurement)
        return measurement

    async def get_measurement(self, user_id: int, measurement_id: int) -> Optional[CustomMeasurement]:
        result = await self.db.execute(
            select(CustomMeasurement).where(CustomMeasurement.user_id == user_id, CustomMeasurement.id == measurement_id)
        )
        return result.scalar_one_or_none()

    async def list_measurements(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        metric_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ):
        stmt = select(CustomMeasurement).where(CustomMeasurement.user_id == user_id)
        if start_date:
            stmt = stmt.where(CustomMeasurement.measured_at >= start_date)
        if end_date:
            stmt = stmt.where(CustomMeasurement.measured_at <= end_date)
        if metric_name:
            stmt = stmt.where(CustomMeasurement.metric_name == metric_name)
        stmt = stmt.order_by(desc(CustomMeasurement.measured_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_measurement(
        self, user_id: int, measurement_id: int, data: CustomMeasurementCreate
    ) -> Optional[CustomMeasurement]:
        measurement = await self.get_measurement(user_id, measurement_id)
        if not measurement:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(measurement, field, value)
        await self.db.flush()
        await self.db.refresh(measurement)
        return measurement

    async def delete_measurement(self, user_id: int, measurement_id: int) -> bool:
        measurement = await self.get_measurement(user_id, measurement_id)
        if not measurement:
            return False
        await self.db.delete(measurement)
        await self.db.flush()
        return True

    async def get_metric_stats(self, user_id: int, metric_name: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """Get statistics for a specific metric over a time period."""
        stmt = select(CustomMeasurement).where(CustomMeasurement.user_id == user_id, CustomMeasurement.metric_name == metric_name)
        if start_date:
            stmt = stmt.where(CustomMeasurement.measured_at >= start_date)
        if end_date:
            stmt = stmt.where(CustomMeasurement.measured_at <= end_date)
        
        result = await self.db.execute(stmt)
        measurements = list(result.scalars().all())
        
        if not measurements:
            return None
            
        values = [m.value for m in measurements]
        return {
            "count": len(measurements),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "unit": measurements[0].unit,
            "start_date": min(m.measured_at for m in measurements),
            "end_date": max(m.measured_at for m in measurements),
        }