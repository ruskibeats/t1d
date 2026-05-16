from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, and_, func
from typing import List, Optional

from app.sleep.models import SleepEntry, SleepStage
from app.sleep.schemas import SleepEntryCreate, SleepStageCreate


class SleepService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_entry(self, user_id: int, data: SleepEntryCreate) -> SleepEntry:
        entry = SleepEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def get_entry(self, user_id: int, entry_id: int) -> Optional[SleepEntry]:
        result = await self.db.execute(
            select(SleepEntry).where(SleepEntry.user_id == user_id, SleepEntry.id == entry_id)
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

    async def update_entry(
        self, user_id: int, entry_id: int, data: SleepEntryCreate
    ) -> Optional[SleepEntry]:
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