"""Pydantic schemas for vitals domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class VitalEntryCreate(BaseModel):
    spo2_percent: Optional[float] = Field(None, ge=50, le=100)
    respiratory_rate: Optional[float] = Field(None, ge=5, le=60)
    body_temperature_c: Optional[float] = Field(None, ge=30, le=45)
    measured_at: datetime
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class VitalEntryResponse(BaseModel):
    id: int
    user_id: int
    spo2_percent: Optional[float]
    respiratory_rate: Optional[float]
    body_temperature_c: Optional[float]
    measured_at: datetime
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
