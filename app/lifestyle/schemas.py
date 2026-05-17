"""Pydantic schemas for lifestyle domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class LifestyleEntryCreate(BaseModel):
    stress_level: Optional[int] = Field(None, ge=1, le=10)
    energy_level: Optional[int] = Field(None, ge=1, le=10)
    caffeine_mg: Optional[float] = Field(None, ge=0, le=2000)
    measured_at: datetime
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class LifestyleEntryResponse(BaseModel):
    id: int
    user_id: int
    stress_level: Optional[int]
    energy_level: Optional[int]
    caffeine_mg: Optional[float]
    measured_at: datetime
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
