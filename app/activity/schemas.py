"""Pydantic schemas for activity domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class ActivityEntryCreate(BaseModel):
    steps: Optional[int] = Field(None, ge=0)
    distance_km: Optional[float] = Field(None, ge=0)
    floors_climbed: Optional[int] = Field(None, ge=0)
    measured_at: datetime
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class ActivityEntryResponse(BaseModel):
    id: int
    user_id: int
    steps: Optional[int]
    distance_km: Optional[float]
    floors_climbed: Optional[int]
    measured_at: datetime
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
