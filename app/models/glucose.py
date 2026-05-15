"""Glucose reading API models (Pydantic schemas)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GlucoseReadingBase(BaseModel):
    """Base glucose reading model."""

    glucose_value: float = Field(..., description="Glucose value", ge=0)
    glucose_units: str = Field("mg/dL", description="Units: mg/dL or mmol/L")
    timestamp: datetime = Field(..., description="Reading timestamp")
    reading_type: str = Field(..., description="Type: sensor, fingerstick, estimated")
    source: str = Field(..., description="Source: dexcom, nightscout, manual")


class GlucoseReadingCreate(GlucoseReadingBase):
    """Glucose reading creation model."""

    source_device_id: str | None = Field(None, description="Source device/transmitter ID")
    trend: str | None = Field(None, description="Trend direction")
    trend_rate: float | None = Field(None, description="Trend rate (mg/dL per min)")
    is_calibration: bool = Field(False, description="Is this a calibration reading")
    is_filtered: bool = Field(False, description="Is this reading filtered")
    confidence_level: int | None = Field(None, description="Confidence level 0-100", ge=0, le=100)


class GlucoseReadingResponse(GlucoseReadingBase):
    """Glucose reading response model."""

    id: int = Field(..., description="Glucose reading ID")
    user_id: int = Field(..., description="User ID")
    source_device_id: str | None = Field(None, description="Source device/transmitter ID")
    trend: str | None = Field(None, description="Trend direction")
    trend_rate: float | None = Field(None, description="Trend rate (mg/dL per min)")
    is_calibration: bool = Field(False, description="Is this a calibration reading")
    is_filtered: bool = Field(False, description="Is this reading filtered")
    confidence_level: int | None = Field(None, description="Confidence level 0-100", ge=0, le=100)
    created_at: datetime = Field(..., description="Record creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
    )


class GlucoseReadingUpdate(BaseModel):
    """Glucose reading update model."""

    glucose_value: float | None = Field(None, description="Glucose value", ge=0)
    timestamp: datetime | None = Field(None, description="Reading timestamp")
    trend: str | None = Field(None, description="Trend direction")
    trend_rate: float | None = Field(None, description="Trend rate (mg/dL per min)")


class GlucoseStats(BaseModel):
    """Glucose statistics response model."""

    average: float = Field(..., description="Average glucose value")
    min_value: float = Field(..., description="Minimum glucose value")
    max_value: float = Field(..., description="Maximum glucose value")
    std_dev: float = Field(..., description="Standard deviation")
    time_in_range: float = Field(..., description="Time in range percentage", ge=0, le=100)
    time_below_range: float = Field(..., description="Time below range percentage", ge=0, le=100)
    time_above_range: float = Field(..., description="Time above range percentage", ge=0, le=100)
    total_readings: int = Field(..., description="Total number of readings")

    model_config = ConfigDict(
        from_attributes=True,
    )


class GlucoseTrend(BaseModel):
    """Glucose trend data point."""

    timestamp: datetime = Field(..., description="Timestamp")
    glucose_value: float = Field(..., description="Glucose value", ge=0)
    trend: str | None = Field(None, description="Trend direction")
