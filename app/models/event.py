"""Context event API models (Pydantic schemas)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Available event types."""

    MEAL = "meal"
    INSULIN = "insulin"
    EXERCISE = "exercise"
    SLEEP = "sleep"
    STRESS = "stress"
    ALCOHOL = "alcohol"
    ILLNESS = "illness"
    MEDICATION = "medication"
    NOTE = "note"


class EventSubtype(str, Enum):
    """Available event subtypes."""

    # Meal subtypes
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"

    # Insulin subtypes
    RAPID = "rapid"
    SHORT = "short"
    LONG = "long"
    ULTRA_LONG = "ultra_long"
    BASAL = "basal"
    BOLUS = "bolus"

    # Exercise subtypes
    CARDIO = "cardio"
    STRENGTH = "strength"
    FLEXIBILITY = "flexibility"
    SPORT = "sport"

    # Sleep subtypes
    NAP = "nap"
    NIGHT = "night"

    # Stress subtypes
    WORK = "work"
    PERSONAL = "personal"
    HEALTH = "health"


class Intensity(str, Enum):
    """Exercise intensity levels."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ContextEventBase(BaseModel):
    """Base context event model."""

    event_type: EventType = Field(..., description="Type of event")
    event_subtype: EventSubtype | None = Field(None, description="Subtype of event")
    timestamp: datetime = Field(..., description="Event timestamp")
    duration: int | None = Field(None, description="Duration in minutes", ge=0)
    description: str | None = Field(None, description="Event description")
    notes: str | None = Field(None, description="Additional notes")


class MealEventData(BaseModel):
    """Meal-specific event data."""

    carbs_grams: float | None = Field(None, description="Carbohydrates in grams", ge=0)
    protein_grams: float | None = Field(None, description="Protein in grams", ge=0)
    fat_grams: float | None = Field(None, description="Fat in grams", ge=0)
    calories: int | None = Field(None, description="Calories", ge=0)


class InsulinEventData(BaseModel):
    """Insulin-specific event data."""

    insulin_units: float | None = Field(None, description="Insulin units", ge=0)
    insulin_type: str | None = Field(None, description="Type of insulin")


class ExerciseEventData(BaseModel):
    """Exercise-specific event data."""

    intensity: Intensity | None = Field(None, description="Exercise intensity")
    heart_rate_avg: int | None = Field(None, description="Average heart rate", ge=0)


class ContextEventCreate(ContextEventBase):
    """Context event creation model."""

    meal_data: MealEventData | None = Field(None, description="Meal-specific data")
    insulin_data: InsulinEventData | None = Field(None, description="Insulin-specific data")
    exercise_data: ExerciseEventData | None = Field(None, description="Exercise-specific data")
    tags: list | None = Field(None, description="Event tags")


class ContextEventResponse(ContextEventBase):
    """Context event response model."""

    id: int = Field(..., description="Event ID")
    user_id: int = Field(..., description="User ID")
    meal_data: MealEventData | None = Field(None, description="Meal-specific data")
    insulin_data: InsulinEventData | None = Field(None, description="Insulin-specific data")
    exercise_data: ExerciseEventData | None = Field(None, description="Exercise-specific data")
    tags: list | None = Field(None, description="Event tags")
    photos: list | None = Field(None, description="Photo references")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
    )


class ContextEventUpdate(BaseModel):
    """Context event update model."""

    event_type: EventType | None = Field(None, description="Type of event")
    event_subtype: EventSubtype | None = Field(None, description="Subtype of event")
    timestamp: datetime | None = Field(None, description="Event timestamp")
    duration: int | None = Field(None, description="Duration in minutes", ge=0)
    description: str | None = Field(None, description="Event description")
    notes: str | None = Field(None, description="Additional notes")
    meal_data: MealEventData | None = Field(None, description="Meal-specific data")
    insulin_data: InsulinEventData | None = Field(None, description="Insulin-specific data")
    exercise_data: ExerciseEventData | None = Field(None, description="Exercise-specific data")
    tags: list | None = Field(None, description="Event tags")
