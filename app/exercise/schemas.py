"""Pydantic schemas for exercise domain."""

from datetime import datetime
from typing import Any, Optional, List

from pydantic import BaseModel, Field, ConfigDict


class ExerciseEntryCreate(BaseModel):
    type: str = Field(..., max_length=50)
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    calories: Optional[float] = Field(None, ge=0)
    heart_rate_avg: Optional[int] = Field(None, ge=30, le=250)
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class ExerciseEntryResponse(BaseModel):
    id: int
    user_id: int
    type: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    calories: Optional[float]
    heart_rate_avg: Optional[int]
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExerciseEntrySetCreate(BaseModel):
    set_number: int = Field(..., gt=0)
    reps: Optional[int] = Field(None, gt=0)
    weight: Optional[float] = Field(None, gt=0)  # kg or lbs
    distance: Optional[float] = Field(None, ge=0)  # km or miles
    duration_seconds: Optional[int] = Field(None, gt=0)  # for timed sets


class ExerciseEntrySetResponse(BaseModel):
    id: int
    entry_id: int
    set_number: int
    reps: Optional[int]
    weight: Optional[float]
    distance: Optional[float]
    duration_seconds: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class ExerciseEntryWithSets(ExerciseEntryResponse):
    sets: List[ExerciseEntrySetResponse] = []

    model_config = ConfigDict(from_attributes=True)
