"""Personal context service for computing user-specific metabolic context.

Computes the user-specific metabolic context needed for meal forecasting
using recent glucose history and stored user parameters.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from app.metrics.types import MetricType
from app.db.models import User, GlucoseReading
from app.metrics.models import HealthMetric


class TrendClass(str, Enum):
    """Trend classification for glucose."""
    RISING = "rising"
    FALLING = "falling"
    FLAT = "flat"
    UNKNOWN = "unknown"


@dataclass
class PersonalContext:
    """User-specific metabolic context for meal forecasting."""
    current_glucose: Optional[float]
    glucose_trend: TrendClass
    glucose_trend_rate: Optional[float]
    hour_of_day: int
    recent_glucose_history: list[float]
    recent_history_hours: int
    confidence: float
    
    def is_reliable(self) -> bool:
        """Return True if context has sufficient data."""
        return self.confidence >= 0.7 and self.current_glucose is not None


@dataclass
class HourOfDayBaseline:
    """Baseline values for a specific hour of day."""
    hour: int
    typical_glucose: float
    variance: float


async def get_personal_context(
    user: User,
    db,
    hours_lookback: int = 24,
) -> PersonalContext:
    """Compute personal context for a user.
    
    Args:
        user: User model instance
        db: Async database session
        hours_lookback: Hours of history to analyze
        
    Returns:
        PersonalContext with glucose history and trend
    """
    now = datetime.now()
    current_hour = now.hour
    
    # Get recent glucose readings
    cutoff = now - timedelta(hours=hours_lookback)
    
    # Query health metrics for glucose
    result = await db.execute(
        "SELECT value, measured_at FROM health_metrics WHERE user_id = :user_id AND type = :type AND measured_at >= :cutoff ORDER BY measured_at DESC LIMIT 50",
        {"user_id": user.id, "type": MetricType.BLOOD_GLUCOSE.value, "cutoff": cutoff}
    )
    
    readings = result.fetchall()
    
    if not readings:
        # Try glucose readings table as fallback
        result2 = await db.execute(
            "SELECT glucose_value, timestamp FROM tbl_glucose_readings WHERE user_id = :user_id AND timestamp >= :cutoff ORDER BY timestamp DESC LIMIT 50",
            {"user_id": user.id, "cutoff": cutoff}
        )
        readings = [(r[0], r[1]) for r in result2.fetchall()]
    
    if not readings:
        return PersonalContext(
            current_glucose=None,
            glucose_trend=TrendClass.UNKNOWN,
            glucose_trend_rate=None,
            hour_of_day=current_hour,
            recent_glucose_history=[],
            recent_history_hours=hours_lookback,
            confidence=0.3,
        )
    
    # Extract values and timestamps
    values = [float(r[0]) for r in readings]
    timestamps = [r[1] for r in readings]
    
    # Sort by timestamp (oldest first)
    paired = sorted(zip(values, timestamps), key=lambda x: x[1])
    sorted_values = [p[0] for p in paired]
    
    current_glucose = sorted_values[-1] if sorted_values else None
    
    # Compute trend from last 3 readings
    trend = TrendClass.UNKNOWN
    trend_rate = None
    
    if len(sorted_values) >= 2:
        recent = sorted_values[-3:]
        if len(recent) == 3:
            # Compute slope: (latest - oldest) / time_span
            # Simplified: use value differences
            diff = recent[-1] - recent[0]
            if diff > 10:
                trend = TrendClass.RISING
                trend_rate = diff / 2  # mg/dL per reading
            elif diff < -10:
                trend = TrendClass.FALLING
                trend_rate = diff / 2
            else:
                trend = TrendClass.FLAT
        else:
            diff = recent[-1] - recent[0]
            if diff > 5:
                trend = TrendClass.RISING
            elif diff < -5:
                trend = TrendClass.FALLING
    
    confidence = min(1.0, len(readings) / 10.0)
    
    return PersonalContext(
        current_glucose=current_glucose,
        glucose_trend=trend,
        glucose_trend_rate=trend_rate,
        hour_of_day=current_hour,
        recent_glucose_history=sorted_values[-10:],  # Last 10 readings
        recent_history_hours=hours_lookback,
        confidence=confidence,
    )


async def get_hour_of_day_baseline(
    user: User,
    db,
    hour: int,
) -> Optional[HourOfDayBaseline]:
    """Get typical glucose for a specific hour of day.
    
    Args:
        user: User model instance
        db: Async database session
        hour: Hour of day (0-23)
        
    Returns:
        HourOfDayBaseline with typical values or None
    """
    # Query daily aggregates for this hour
    result = await db.execute(
        """SELECT AVG(value) as avg_value, STDDEV(value) as std_value 
           FROM health_metrics 
           WHERE user_id = :user_id AND type = :type 
           AND EXTRACT(HOUR FROM measured_at) = :hour""",
        {"user_id": user.id, "type": MetricType.BLOOD_GLUCOSE.value, "hour": hour}
    )
    
    row = result.fetchone()
    
    if row and row[0]:
        return HourOfDayBaseline(
            hour=hour,
            typical_glucose=float(row[0]),
            variance=float(row[1]) if row[1] else 20.0,
        )
    
    return None