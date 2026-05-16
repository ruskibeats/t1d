"""Pydantic schemas for fasting domain."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FastingEntryCreate(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    source: str = "manual"


class FastingEntryResponse(BaseModel):
    id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True