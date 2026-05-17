"""Pydantic schemas for mood domain."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class MoodEntryCreate(BaseModel):
    score: int = Field(..., ge=1, le=10)  # 1-10 scale
    notes: Optional[str] = None
    logged_at: datetime
    source: str = "manual"


class MoodEntryResponse(BaseModel):
    id: int
    user_id: int
    score: int
    notes: Optional[str]
    logged_at: datetime
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
