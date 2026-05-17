"""Insight models for proactive, pattern-driven diabetic companion.

These models represent actionable insights generated from pattern analysis.
All insights are educational and include appropriate medical disclaimers.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InsightType(str, Enum):
    """Types of proactive insights."""
    
    TIME_OF_DAY_SPIKE = "time_of_day_spike"
    TIME_OF_DAY_LOW = "time_of_day_low"
    MEAL_SPIKE = "meal_spike"
    PRE_MEAL_PREDICTION = "pre_meal_prediction"
    TREND_ALERT = "trend_alert"


class InsightSeverity(str, Enum):
    """Severity levels for insights."""
    
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class TimeOfDayPattern(BaseModel):
    """A recurring glucose pattern at a specific time of day."""
    
    type: InsightType = InsightType.TIME_OF_DAY_SPIKE
    severity: InsightSeverity = InsightSeverity.MODERATE
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    hour_range: str = Field(..., description="Human-readable time range")
    description: str = Field(..., description="Human-readable pattern description")
    detail: str = Field(..., description="Detailed statistical explanation")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    data_points: int = Field(..., description="Number of data points analyzed")
    avg_value: float = Field(..., description="Average glucose value during this time")
    recommendation: str = Field(..., description="Safety-compliant recommendation")
    disclaimer: str = Field(default="This is not medical advice. Always consult your healthcare provider.")

    model_config = ConfigDict(from_attributes=True)


class MealPattern(BaseModel):
    """A correlation between a specific food and glucose outcome."""
    
    type: InsightType = InsightType.MEAL_SPIKE
    severity: InsightSeverity = InsightSeverity.MODERATE
    food_name: str = Field(..., description="Name of the food")
    occurrences: int = Field(..., description="Number of times this food was logged")
    description: str = Field(..., description="Human-readable pattern description")
    detail: str = Field(..., description="Detailed statistical explanation")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    avg_peak_glucose: float = Field(..., description="Average peak glucose after this food")
    avg_time_to_peak_min: float = Field(..., description="Average minutes to reach peak")
    recommendation: str = Field(..., description="Safety-compliant recommendation")
    disclaimer: str = Field(default="This is not medical advice. Always consult your healthcare provider.")

    model_config = ConfigDict(from_attributes=True)


class PreMealPrediction(BaseModel):
    """A predicted glucose outcome for a planned meal."""
    
    type: InsightType = InsightType.PRE_MEAL_PREDICTION
    food_name: str = Field(..., description="Name of the food")
    based_on_meals: int = Field(..., description="Number of historical meals used")
    predicted_peak: float = Field(..., description="Predicted peak glucose value")
    predicted_time_to_peak_min: float = Field(..., description="Predicted minutes to peak")
    message: str = Field(..., description="Human-readable prediction")
    current_status: str | None = Field(None, description="Current glucose context")
    recommendation: str = Field(..., description="Safety-compliant recommendation")
    disclaimer: str = Field(
        default="This is a prediction based on your historical data, not medical advice. "
                "Always consult your healthcare provider for insulin dosing decisions."
    )

    model_config = ConfigDict(from_attributes=True)


class GlucoseSummary(BaseModel):
    """Summary of recent glucose data."""
    
    period: str = Field(..., description="Time period for the summary")
    total_readings: int = Field(..., description="Total number of readings")
    avg_glucose: float = Field(..., description="Average glucose value")
    time_in_range_pct: float = Field(..., description="Percentage of time in target range")
    min_glucose: float = Field(..., description="Minimum glucose value")
    max_glucose: float = Field(..., description="Maximum glucose value")


class InsightsResponse(BaseModel):
    """Complete insights response for a user."""
    
    generated_at: datetime = Field(..., description="When these insights were generated")
    summary: GlucoseSummary | None = Field(None, description="Recent glucose summary")
    time_of_day_patterns: list[TimeOfDayPattern] = Field(default_factory=list)
    meal_patterns: list[MealPattern] = Field(default_factory=list)
    total_insights: int = Field(..., description="Total number of insights")
    disclaimer: str = Field(
        default="These insights are generated from your glucose data and are "
                "for educational purposes only. They are not medical advice. "
                "Always consult your healthcare provider before making any "
                "changes to your diabetes management."
    )

    model_config = ConfigDict(from_attributes=True)


class PreMealRequest(BaseModel):
    """Request model for pre-meal prediction."""
    
    food_name: str = Field(..., description="Name of the food the user is about to eat")
    current_glucose: float | None = Field(None, description="Current glucose reading if available")