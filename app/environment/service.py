"""Service layer for environment domain."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from app.environment.models import EnvironmentEntry
from app.environment.schemas import EnvironmentEntryCreate


class EnvironmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: EnvironmentEntryCreate) -> EnvironmentEntry:
        entry = EnvironmentEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def get(self, user_id: int, entry_id: int) -> Optional[EnvironmentEntry]:
        result = await self.db.execute(
            select(EnvironmentEntry).where(EnvironmentEntry.user_id == user_id, EnvironmentEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EnvironmentEntry]:
        stmt = select(EnvironmentEntry).where(EnvironmentEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(EnvironmentEntry.measured_at >= start_date)
        if end_date:
            stmt = stmt.where(EnvironmentEntry.measured_at <= end_date)
        stmt = stmt.order_by(desc(EnvironmentEntry.measured_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, user_id: int, entry_id: int, data: EnvironmentEntryCreate
    ) -> Optional[EnvironmentEntry]:
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