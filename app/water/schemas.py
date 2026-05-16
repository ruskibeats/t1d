"""Pydantic schemas for water tracking domain."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WaterEntryCreate(BaseModel):
    amount_ml: float = Field(..., gt=0)
    logged_at: datetime
    source: str = "manual"


class WaterEntryResponse(BaseModel):
    id: int
    user_id: int
    amount_ml: float
    logged_at: datetime
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
