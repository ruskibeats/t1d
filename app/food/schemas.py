"""Pydantic schemas for food domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class FoodCreate(BaseModel):
    name: str = Field(..., max_length=255)
    brand_name: Optional[str] = None
    serving_size: Optional[float] = Field(None, ge=0)
    serving_unit: Optional[str] = Field("g", max_length=50)
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    saturated_fat: Optional[float] = None
    fiber: Optional[float] = None
    sugars: Optional[float] = None
    sodium: Optional[float] = None
    barcode: Optional[str] = None
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class FoodResponse(BaseModel):
    id: int
    user_id: int
    name: str
    brand_name: Optional[str]
    serving_size: Optional[float]
    serving_unit: Optional[str]
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]
    saturated_fat: Optional[float]
    fiber: Optional[float]
    sugars: Optional[float]
    sodium: Optional[float]
    barcode: Optional[str]
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FoodSearchResult(BaseModel):
    """Combined search result from personal + external providers."""
    name: str
    brand_name: Optional[str] = None
    serving_size: Optional[float] = None
    serving_unit: Optional[str] = "g"
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugars: Optional[float] = None
    barcode: Optional[str] = None
    source: str = "manual"
    source_provider: str = "manual"  # "personal", "openfoodfacts", "usda"
    food_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class FoodEntryCreate(BaseModel):
    food_id: Optional[int] = None
    quantity: float = Field(1, gt=0)
    unit: str = Field("serving", max_length=50)
    entry_date: datetime
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    food_name: Optional[str] = None
    brand_name: Optional[str] = None
    serving_size: Optional[float] = None
    serving_unit: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugars: Optional[float] = None
    glycemic_index: Optional[str] = None
    glycemic_load: Optional[float] = None
    source: str = "manual"
    meta: Optional[dict[str, Any]] = None


class FoodEntryResponse(BaseModel):
    id: int
    user_id: int
    food_id: Optional[int]
    quantity: float
    unit: str
    entry_date: datetime
    meal_type: str
    food_name: Optional[str]
    brand_name: Optional[str]
    serving_size: Optional[float]
    serving_unit: Optional[str]
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]
    fiber: Optional[float]
    sugars: Optional[float]
    glycemic_index: Optional[str]
    glycemic_load: Optional[float]
    source: str
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
