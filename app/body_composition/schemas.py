"""Pydantic schemas for body composition domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class BodyCompositionEntryCreate(BaseModel):
    weight_kg: Optional[float] = Field(None, ge=20, le=300)
    body_fat_percent: Optional[float] = Field(None, ge=1, le=70)
    bmi: Optional[float] = Field(None, ge=10, le=60)
    lean_mass_kg: Optional[float] = Field(None, ge=10, le=200)
    waist_cm: Optional[float] = Field(None, ge=30, le=200)
    measured_at: datetime
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class BodyCompositionEntryResponse(BaseModel):
    id: int
    user_id: int
    weight_kg: Optional[float]
    body_fat_percent: Optional[float]
    bmi: Optional[float]
    lean_mass_kg: Optional[float]
    waist_cm: Optional[float]
    measured_at: datetime
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
