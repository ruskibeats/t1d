"""Pydantic schemas for body battery domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class BodyBatteryEntryCreate(BaseModel):
    value: Optional[float] = Field(None, ge=0, le=100)
    change: Optional[float] = Field(None, ge=-100, le=100)
    charged: Optional[float] = Field(None, ge=0, le=100)
    drained: Optional[float] = Field(None, ge=0, le=100)
    measured_at: datetime
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class BodyBatteryEntryResponse(BaseModel):
    id: int
    user_id: int
    value: Optional[float]
    change: Optional[float]
    charged: Optional[float]
    drained: Optional[float]
    measured_at: datetime
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
