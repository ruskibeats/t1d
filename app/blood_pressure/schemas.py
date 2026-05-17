"""Pydantic schemas for blood pressure domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class BloodPressureEntryCreate(BaseModel):
    systolic: float = Field(..., ge=50, le=300)
    diastolic: float = Field(..., ge=30, le=200)
    measured_at: datetime
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class BloodPressureEntryResponse(BaseModel):
    id: int
    user_id: int
    systolic: float
    diastolic: float
    measured_at: datetime
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
