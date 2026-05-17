"""Pydantic schemas for heart rate domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class HeartRateEntryCreate(BaseModel):
    heart_rate_bpm: Optional[float] = Field(None, ge=20, le=300)
    resting_heart_rate_bpm: Optional[float] = Field(None, ge=20, le=200)
    hrv_ms: Optional[float] = Field(None, ge=0, le=500)
    measured_at: datetime
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class HeartRateEntryResponse(BaseModel):
    id: int
    user_id: int
    heart_rate_bpm: Optional[float]
    resting_heart_rate_bpm: Optional[float]
    hrv_ms: Optional[float]
    measured_at: datetime
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
