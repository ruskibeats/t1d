"""Hour-of-day baseline and variability features.

Computes baseline glucose metrics by hour of day for use in meal forecasting.
"""

from dataclasses import dataclass
from typing import Optional

from app.services.personal_context_service import HourOfDayBaseline
from app.db.models import User


@dataclass
class HourBaselineFeatures:
    """Baseline features for a specific hour of day."""
    hour: int
    mean_glucose: Optional[float] = None
    median_glucose: Optional[float] = None
    min_glucose: Optional[float] = None
    max_glucose: Optional[float] = None
    std_deviation: Optional[float] = None
    sample_count: int = 0
    recentness_hours: int = 0
    stability_level: str = "unknown"
    
    def is_trusted(self, min_samples: int = 5) -> bool:
        """Return True if baseline has sufficient data."""
        return self.sample_count >= min_samples and self.mean_glucose is not None


@dataclass
class GlucoseStability:
    """Glucose stability assessment."""
    level: str  # "stable", "variable", "volatile", "unknown"
    variability_score: float  # 0.0 to 1.0


async def compute_hour_baseline_features(
    user: User,
    db,
    hour: int,
    days_lookback: int = 30,
) -> HourBaselineFeatures:
    """Compute baseline features for a specific hour of day.
    
    Args:
        user: User model instance
        db: Async database session
        hour: Hour of day (0-23)
        days_lookback: Days of history to consider
        
    Returns:
        HourBaselineFeatures with computed metrics
    """
    from app.metrics.types import MetricType
    
    # Query glucose values for this hour across days
    result = await db.execute(
        """SELECT value, measured_at 
           FROM health_metrics 
           WHERE user_id = :user_id AND type = :type 
           AND EXTRACT(HOUR FROM measured_at AT TIME ZONE 'UTC') = :hour
           AND measured_at >= NOW() - INTERVAL ':days days'
           ORDER BY measured_at DESC""",
        {"user_id": user.id, "type": MetricType.BLOOD_GLUCOSE.value, "hour": hour, "days": days_lookback}
    )
    
    rows = result.fetchall()
    
    if not rows:
        # Fallback to glucose_readings
        result2 = await db.execute(
            """SELECT glucose_value, timestamp 
               FROM tbl_glucose_readings 
               WHERE user_id = :user_id 
               AND EXTRACT(HOUR FROM timestamp AT TIME ZONE 'UTC') = :hour
               AND timestamp >= NOW() - INTERVAL ':days days'
               ORDER BY timestamp DESC""",
            {"user_id": user.id, "hour": hour, "days": days_lookback}
        )
        rows = result2.fetchall()
    
    if not rows:
        return HourBaselineFeatures(hour=hour, stability_level="unknown")
    
    values = [float(r[0]) for r in rows]
    
    # Compute statistics
    mean_val = sum(values) / len(values)
    sorted_vals = sorted(values)
    median_val = sorted_vals[len(sorted_vals) // 2]
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    
    # Standard deviation
    variance = sum((v - mean_val) ** 2 for v in values) / len(values)
    std_val = variance ** 0.5
    
    # Determine stability level
    if std_val <= 15:
        stability = "stable"
    elif std_val <= 30:
        stability = "variable"
    else:
        stability = "volatile"
    
    return HourBaselineFeatures(
        hour=hour,
        mean_glucose=mean_val,
        median_glucose=median_val,
        min_glucose=min_val,
        max_glucose=max_val,
        std_deviation=std_val,
        sample_count=len(values),
        recentness_hours=days_lookback * 24,
        stability_level=stability,
    )


def assess_glucose_stability(features: HourBaselineFeatures) -> GlucoseStability:
    """Assess glucose stability from baseline features.
    
    Args:
        features: HourBaselineFeatures to assess
        
    Returns:
        GlucoseStability with level and score
    """
    if features.std_deviation is None:
        return GlucoseStability(level="unknown", variability_score=0.5)
    
    # Normalize variability score (0-1)
    std = features.std_deviation
    if std <= 10:
        score = 0.0
    elif std <= 20:
        score = 0.3
    elif std <= 35:
        score = 0.6
    else:
        score = 1.0
    
    level = features.stability_level
    
    return GlucoseStability(level=level, variability_score=score)


async def get_morning_sensitivity_flag(
    user: User,
    db,
    morning_hours: tuple = (6, 7, 8, 9, 10),
) -> bool:
    """Determine if user shows morning glucose sensitivity.
    
    Morning sensitivity is indicated by consistently higher morning readings
    or rapid rises after waking.
    
    Args:
        user: User model instance
        db: Async database session
        morning_hours: Hours considered "morning"
        
    Returns:
        True if morning sensitivity appears likely
    """
    morning_features = []
    
    for hour in morning_hours:
        features = await compute_hour_baseline_features(user, db, hour)
        if features.is_trusted(min_samples=3):
            morning_features.append(features)
    
    if len(morning_features) < 3:
        return False
    
    # Check if morning averages are higher than overall
    morning_means = [f.mean_glucose for f in morning_features if f.mean_glucose]
    if len(morning_means) < 3:
        return False
    
    avg_morning = sum(morning_means) / len(morning_means)
    
    # Compare to afternoon baseline
    afternoon_features = await compute_hour_baseline_features(user, db, 14)
    if afternoon_features.mean_glucose:
        afternoon_mean = afternoon_features.mean_glucose
        # Morning is considered sensitive if 20+ mg/dL higher
        return avg_morning > afternoon_mean + 20
    
    return False


async def get_volatility_indicator(
    user: User,
    db,
) -> tuple[bool, float]:
    """Check if user has recent volatility in glucose readings.
    
    Args:
        user: User model instance
        db: Async database session
        
    Returns:
        Tuple of (is_volatile, volatility_score)
    """
    from app.metrics.types import MetricType
    from datetime import datetime, timedelta
    
    # Get recent readings (last 24 hours)
    cutoff = datetime.now() - timedelta(hours=24)
    
    result = await db.execute(
        """SELECT value FROM health_metrics 
           WHERE user_id = :user_id AND type = :type 
           AND measured_at >= :cutoff
           ORDER BY measured_at DESC LIMIT 50""",
        {"user_id": user.id, "type": MetricType.BLOOD_GLUCOSE.value, "cutoff": cutoff}
    )
    
    rows = result.fetchall()
    values = [float(r[0]) for r in rows]
    
    if len(values) < 5:
        return False, 0.0
    
    # Compute intra-day variability
    mean_val = sum(values) / len(values)
    variance = sum((v - mean_val) ** 2 for v in values) / len(values)
    std_val = variance ** 0.5
    
    # Volatility score
    is_volatile = std_val > 40  # High variability threshold
    volatility_score = min(1.0, std_val / 60)  # Normalize
    
    return is_volatile, volatility_score