"""Pattern analysis API models (Pydantic schemas)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PatternType(str, Enum):
    """Available pattern types."""

    POST_MEAL_SPIKE = "post_meal_spike"
    OVERNIGHT_LOW = "overnight_low"
    DAWN_PHENOMENON = "dawn_phenomenon"
    EXERCISE_EFFECT = "exercise_effect"
    DELAYED_HIGH_FAT = "delayed_high_fat"
    TIME_IN_RANGE = "time_in_range"
    CORRELATION = "correlation"


class PatternAnalysisBase(BaseModel):
    """Base pattern analysis model."""

    pattern_type: PatternType = Field(..., description="Type of pattern")
    time_period: str = Field(..., description="Time period: daily, weekly, monthly")
    start_date: datetime = Field(..., description="Analysis start date")
    end_date: datetime = Field(..., description="Analysis end date")


class PatternAnalysisCreate(PatternAnalysisBase):
    """Pattern analysis creation model."""

    user_id: int = Field(..., description="User ID")


class PatternAnalysisResponse(PatternAnalysisBase):
    """Pattern analysis response model."""

    id: int = Field(..., description="Pattern analysis ID")
    user_id: int = Field(..., description="User ID")
    summary: str = Field(..., description="Pattern summary")
    findings: dict = Field(..., description="Pattern findings")
    statistics: dict = Field(..., description="Statistical data")
    recommendations: list[str] | None = Field(None, description="Recommendations")
    created_at: datetime = Field(..., description="Record creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
    )


class PatternDetectionRequest(BaseModel):
    """Request model for pattern detection."""

    pattern_types: list[PatternType] | None = Field(
        None,
        description="Types of patterns to detect (default: all)",
    )
    start_date: datetime | None = Field(None, description="Start date for analysis")
    end_date: datetime | None = Field(None, description="End date for analysis")
    include_statistics: bool = Field(True, description="Include statistical data")


class PatternDetectionResponse(BaseModel):
    """Response model for pattern detection."""

    patterns: list[PatternAnalysisResponse] = Field(..., description="Detected patterns")
    total_count: int = Field(..., description="Total number of patterns")

    model_config = ConfigDict(
        from_attributes=True,
    )


class PatternCorrelation(BaseModel):
    """Pattern correlation model."""

    event_type: str = Field(..., description="Type of correlated event")
    correlation_strength: float = Field(..., description="Correlation strength", ge=-1, le=1)
    description: str = Field(..., description="Correlation description")
    statistical_significance: float = Field(..., description="P-value", ge=0, le=1)


class PatternSummary(BaseModel):
    """Pattern summary for conversational responses."""

    pattern_type: PatternType = Field(..., description="Type of pattern")
    description: str = Field(..., description="Human-readable description")
    severity: str = Field(..., description="Severity: low, moderate, high")
    action_items: list[str] | None = Field(None, description="Suggested actions")
    confidence: float = Field(..., description="Confidence level", ge=0, le=1)

    model_config = ConfigDict(
        from_attributes=True,
    )
