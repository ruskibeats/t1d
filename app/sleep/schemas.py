"""Pydantic schemas for sleep domain."""

from datetime import datetime
from typing import Any, Optional, List

from pydantic import BaseModel, Field


class SleepEntryCreate(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    quality_score: Optional[float] = Field(None, ge=0, le=100)
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class SleepEntryResponse(BaseModel):
    id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    quality_score: Optional[float]
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SleepStageCreate(BaseModel):
    stage_type: str = Field(..., pattern="^(awake|light|deep|rem)$")
    duration_minutes: int = Field(..., gt=0)
    start_time: datetime


class SleepStageResponse(BaseModel):
    id: int
    entry_id: int
    stage_type: str
    duration_minutes: int
    start_time: datetime

    class Config:
        from_attributes = True


class SleepEntryWithStages(SleepEntryResponse):
    stages: List[SleepStageResponse] = []

    class Config:
        from_attributes = True