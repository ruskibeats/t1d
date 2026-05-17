"""Pydantic schemas for measurements domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class CustomMeasurementCreate(BaseModel):
    metric_name: str = Field(..., max_length=100)
    value: float = Field(..., gt=0)
    unit: str = Field(..., max_length=20)
    measured_at: datetime
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class CustomMeasurementResponse(BaseModel):
    id: int
    user_id: int
    metric_name: str
    value: float
    unit: str
    measured_at: datetime
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
