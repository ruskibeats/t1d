"""Pydantic schemas for environment domain."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class EnvironmentEntryCreate(BaseModel):
    temperature_c: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity_percent: Optional[float] = Field(None, ge=0, le=100, description="Humidity percentage 0-100")
    altitude_m: Optional[float] = Field(None, description="Altitude in meters above sea level")
    measured_at: datetime
    source: str = "manual"


class EnvironmentEntryResponse(BaseModel):
    id: int
    user_id: int
    temperature_c: Optional[float]
    humidity_percent: Optional[float]
    altitude_m: Optional[float]
    measured_at: datetime
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)