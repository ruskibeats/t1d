"""Pattern detection and analysis service for T1D data.

Implements time-in-range calculations, post-meal spike detection,
overnight hypoglycemia detection, exercise impact analysis,
and correlation detection between glucose patterns and lifestyle events.
"""

import asyncio
import logging
import statistics
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models import ContextEvent, GlucoseReading, User
from app.models.pattern import (
    PatternAnalysisCreate,
    PatternAnalysisResponse,
    PatternDetectionRequest,
    PatternDetectionResponse,
    PatternCorrelation,
    PatternType,
)

logger = logging.getLogger(__name__)


class PatternAnalysisError(Exception):
    """Raised when pattern analysis fails."""
    pass


class PatternService:
    """Service for detecting and analyzing glucose patterns.
    
    Performs statistical analysis on glucose data to identify:
    - Time-in-range (TIR) metrics
    - Post-meal glucose spikes
    - Overnight hypoglycemia
    - Exercise-related glucose changes
    - Delayed high-fat meal effects
    - Correlations with lifestyle events
    """
    
    # Glucose thresholds (mg/dL)
    HYPO_THRESHOLD = 70      # Below this is low
    HYPO_SEVERE = 54         # Below this is severe hypoglycemia  
    HYPER_THRESHOLD = 180    # Above this is high
    HYPER_SEVERE = 250       # Above this is severe hyperglycemia
    
    # Target range (ADA standard)
    TIR_LOW = 70
    TIR_HIGH = 180
    
    # Time windows (hours)
    POST_MEAL_WINDOW = 3      # Hours after meal to check for spikes
    OVERNIGHT_START = 22      # 10 PM
    OVERNIGHT_END = 6         # 6 AM
    EXERCISE_WINDOW = 12      # Hours after exercise to monitor
    
    def __init__(self):
        """Initialize pattern service."""
        self.logger = logging.getLogger(f"{__name__}.PatternService")
    
    # -------------------------------------------------------------------
    # Time-in-Range Analysis
    # -------------------------------------------------------------------
    
    async def calculate_time_in_range(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Calculate time-in-range statistics for glucose readings.
        
        Args:
            session: Database session
            user_id: ID of the user
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Dictionary with TIR statistics
        """
        # Get all glucose readings in range
        result = await session.execute(
            select(GlucoseReading)
            .where(
                GlucoseReading.user_id == user_id,
                GlucoseReading.timestamp >= start_date,
                GlucoseReading.timestamp <= end_date,
            )
            .order_by(GlucoseReading.timestamp)
        )
        
        readings = result.scalars().all()
        
        if not readings:
            return self._empty_tir_result()
        
        values = [r.glucose_value for r in readings]
        timestamps = [r.timestamp for r in readings]
        
        # Calculate basic statistics
        avg_glucose = statistics.mean(values)
        min_glucose = min(values)
        max_glucose = max(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        # Count readings in different ranges
        total = len(values)
        in_range = sum(1 for v in values if self.TIR_LOW <= v <= self.TIR_HIGH)
        below_range = sum(1 for v in values if v < self.TIR_LOW)
        above_range = sum(1 for v in values if v > self.TIR_HIGH)
        
        # Severe ranges
        severe_low = sum(1 for v in values if v < self.HYPO_SEVERE)
        severe_high = sum(1 for v in values if v > self.HYPER_SEVERE)
        
        # Calculate percentages
        pct_in_range = (in_range / total * 100) if total > 0 else 0
        pct_below = (below_range / total * 100) if total > 0 else 0
        pct_above = (above_range / total * 100) if total > 0 else 0
        pct_severe_low = (severe_low / total * 100) if total > 0 else 0
        pct_severe_high = (severe_high / total * 100) if total > 0 else 0
        
        # Estimated A1C (using formula: (avg_glucose + 46.7) / 28.7)
        estimated_a1c = round((avg_glucose + 46.7) / 28.7, 1) if avg_glucose else 0
        
        # Glucose variability (coefficient of variation)
        cv = (std_dev / avg_glucose * 100) if avg_glucose > 0 else 0
        
        return {
            "period": {
                "start": start_date,
                "end": end_date,
                "duration_hours": round((end_date - start_date).total_seconds() / 3600, 1),
            },
            "readings": {
                "total": total,
                "average": round(avg_glucose, 1),
                "min": round(min_glucose, 1),
                "max": round(max_glucose, 1),
                "std_dev": round(std_dev, 1),
                "coefficient_of_variation": round(cv, 1),
            },
            "time_in_range": {
                "percentage": round(pct_in_range, 1),
                "target_low": self.TIR_LOW,
                "target_high": self.TIR_HIGH,
                "below_range": {
                    "count": below_range,
                    "percentage": round(pct_below, 1),
                    "severe_count": severe_low,
                    "severe_percentage": round(pct_severe_low, 1),
                },
                "above_range": {
                    "count": above_range,
                    "percentage": round(pct_above, 1),
                    "severe_count": severe_high,
                    "severe_percentage": round(pct_severe_high, 1),
                },
            },
            "estimated_a1c": estimated_a1c,
            "grade": self._calculate_grade(pct_in_range, pct_below),
        }
    
    def _calculate_grade(self, pct_in_range: float, pct_below: float) -> str:
        """Calculate overall glucose control grade.
        
        Args:
            pct_in_range: Percentage of readings in target range
            pct_below: Percentage of readings below range
            
        Returns:
            Grade letter (A-F)
        """
        if pct_in_range >= 70 and pct_below < 4:
            return "A"
        if pct_in_range >= 60 and pct_below < 5:
            return "B"
        if pct_in_range >= 50:
            return "C"
        if pct_in_range >= 40:
            return "D"
        return "F"
    
    def _empty_tir_result(self) -> Dict[str, Any]:
        """Return empty TIR result structure."""
        return {
            "period": {"start": None, "end": None, "duration_hours": 0},
            "readings": {"total": 0, "average": 0, "min": 0, "max": 0, "std_dev": 0, "coefficient_of_variation": 0},
            "time_in_range": {
                "percentage": 0,
                "target_low": self.TIR_LOW,
                "target_high": self.TIR_HIGH,
                "below_range": {"count": 0, "percentage": 0, "severe_count": 0, "severe_percentage": 0},
                "above_range": {"count": 0, "percentage": 0, "severe_count": 0, "severe_percentage": 0},
            },
            "estimated_a1c": 0,
            "grade": "N/A",
        }


# ---------------------------------------------------------------------------
# Post-Meal Spike Detection
# ---------------------------------------------------------------------------

    async def detect_post_meal_spikes(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        min_carbs: float = 30,
        spike_threshold: float = 50,  # mg/dL rise from pre-meal
    ) -> List[Dict[str, Any]]:
        """Detect post-meal glucose spikes.
        
        Identifies meals followed by significant glucose increases
        within the post-meal window.
        
        Args:
            session: Database session
            user_id: ID of the user
            start_date: Start of analysis period
            end_date: End of analysis period
            min_carbs: Minimum carbs to consider (default 30g)
            spike_threshold: Minimum glucose rise to count as spike (mg/dL)
            
        Returns:
            List of detected post-meal spike events
        """
        # Get meal events with sufficient carbs
        result = await session.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.event_type == "meal",
                ContextEvent.timestamp >= start_date,
                ContextEvent.timestamp <= end_date,
                ContextEvent.carbs_grams >= min_carbs,
            )
            .order_by(ContextEvent.timestamp)
        )
        
        meals = result.scalars().all()
        spikes = []
        
        for event in meals:
            # Get glucose readings around this meal
            window_end = event.timestamp + timedelta(hours=self.POST_MEAL_WINDOW)
            
            # Get readings from 1 hour before to POST_MEAL_WINDOW after
            window_start = event.timestamp - timedelta(hours=1)
            
            readings_result = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= window_start,
                    GlucoseReading.timestamp <= window_end,
                )
                .order_by(GlucoseReading.timestamp)
            )
            
            readings = readings_result.scalars().all()
            
            if len(readings) < 2:
                continue
            
            # Find pre-meal baseline (readings before meal)
            pre_meal_readings = [
                r for r in readings if r.timestamp < event.timestamp
            ]
            
            # Find peak after meal
            post_meal_readings = [
                r for r in readings if r.timestamp >= event.timestamp
            ]
            
            if not pre_meal_readings or not post_meal_readings:
                continue
            
            # Use average of pre-meal readings as baseline
            pre_meal_avg = statistics.mean([r.glucose_value for r in pre_meal_readings])
            
            # Find peak glucose after meal
            peak_reading = max(post_meal_readings, key=lambda r: r.glucose_value)
            peak_value = peak_reading.glucose_value
            peak_time = peak_reading.timestamp
            
            # Calculate rise from baseline
            glucose_rise = peak_value - pre_meal_avg
            
            # Check if this qualifies as a spike
            if glucose_rise >= spike_threshold and peak_value > self.HYPER_THRESHOLD:
                time_to_peak = (peak_time - event.timestamp).total_seconds() / 60
                
                spikes.append({
                    "meal": {
                        "timestamp": event.timestamp,
                        "carbohydrates": event.carbs_grams,
                        "food_name": event.description or "Meal",
                    },
                    "pre_meal_baseline": round(pre_meal_avg, 1),
                    "peak_value": round(peak_value, 1),
                    "glucose_rise": round(glucose_rise, 1),
                    "time_to_peak_minutes": round(time_to_peak),
                    "severity": self._classify_spike_severity(glucose_rise, peak_value),
                    "exceeds_target": peak_value > self.TIR_HIGH,
                    "recommendations": self._generate_spike_recommendations(
                        meal.carbs_grams, glucose_rise, time_to_peak
                    ),
                })
        
        return spikes
    
    def _classify_spike_severity(self, glucose_rise: float, peak_value: float) -> str:
        """Classify spike severity.
        
        Args:
            glucose_rise: Glucose increase from baseline (mg/dL)
            peak_value: Peak glucose value (mg/dL)
            
        Returns:
            Severity classification
        """
        if peak_value >= self.HYPER_SEVERE or glucose_rise >= 100:
            return "severe"
        if peak_value >= self.HYPER_THRESHOLD or glucose_rise >= 70:
            return "moderate"
        if glucose_rise >= 50:
            return "mild"
        return "minor"
    
    def _generate_spike_recommendations(
        self,
        carbs: float,
        glucose_rise: float,
        time_to_peak: float,
    ) -> List[str]:
        """Generate recommendations for managing post-meal spikes.
        
        Args:
            carbs: Carbohydrate amount (grams)
            glucose_rise: Glucose increase (mg/dL)
            time_to_peak: Time to peak (minutes)
            
        Returns:
            List of recommendation strings
        """
        recs = []
        
        if carbs > 60:
            recs.append("Consider smaller portion sizes for high-carb meals")
        
        if time_to_peak < 60:
            recs.append("Try pre-bolusing 15-30 minutes before eating")
        
        if glucose_rise > 80:
            recs.append("Consider splitting carbs across multiple smaller meals")
            recs.append("Increase fiber intake to slow glucose absorption")
        
        if carbs > 50 and time_to_peak < 90:
            recs.append("Extended or combination bolus may help with rapid spikes")
        
        recs.append("Light activity (15 min walk) after meals can reduce spikes")
        
        return recs


# ---------------------------------------------------------------------------
# Overnight Hypoglycemia Detection
# ---------------------------------------------------------------------------

    async def detect_overnight_hypoglycemia(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Detect overnight hypoglycemia events.
        
        Identifies dangerous lows during sleep hours.
        
        Args:
            session: Database session
            user_id: ID of the user
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            List of overnight hypoglycemia events
        """
        # Get all overnight periods
        current = start_date.replace(hour=self.OVERNIGHT_START, minute=0, second=0)
        if current < start_date:
            current += timedelta(days=1)
        
        hypoglycemia_events = []
        
        while current < end_date:
            overnight_end = current + timedelta(hours=8)  # 10 PM to 6 AM
            
            if overnight_end > end_date:
                break
            
            # Get glucose readings during this overnight period
            result = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= current,
                    GlucoseReading.timestamp <= overnight_end,
                )
                .order_by(GlucoseReading.timestamp)
            )
            
            readings = result.scalars().all()
            
            if not readings:
                current += timedelta(days=1)
                continue
            
            # Find lows
            low_readings = [r for r in readings if r.glucose_value < self.HYPO_THRESHOLD]
            severe_low_readings = [r for r in readings if r.glucose_value < self.HYPO_SEVERE]
            
            if low_readings:
                min_glucose = min(low_readings, key=lambda r: r.glucose_value)
                duration = len(low_readings) / len(readings) * 100 if readings else 0
                
                hypoglycemia_events.append({
                    "date": current.date(),
                    "overnight_period": {
                        "start": current,
                        "end": overnight_end,
                    },
                    "low_count": len(low_readings),
                    "severe_low_count": len(severe_low_readings),
                    "lowest_value": round(min_glucose.glucose_value, 1),
                    "lowest_time": min_glucose.timestamp,
                    "percentage_of_night": round(duration, 1),
                    "severity": self._classify_hypo_severity(min_glucose.glucose_value, duration),
                    "trend_at_lowest": min_glucose.trend or "unknown",
                })
            
            current += timedelta(days=1)
        
        return hypoglycemia_events
    
    def _classify_hypo_severity(self, min_value: float, duration_pct: float) -> str:
        """Classify hypoglycemia severity.
        
        Args:
            min_value: Lowest glucose value (mg/dL)
            duration_pct: Percentage of night spent low
            
        Returns:
            Severity classification
        """
        if min_value < self.HYPO_SEVERE or duration_pct > 50:
            return "severe"
        if min_value < self.HYPO_THRESHOLD or duration_pct > 20:
            return "moderate"
        return "mild"


# ---------------------------------------------------------------------------
# Exercise Impact Analysis
# ---------------------------------------------------------------------------

    async def analyze_exercise_impact(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Analyze the impact of exercise on glucose levels.
        
        Correlates exercise events with subsequent glucose changes.
        
        Args:
            session: Database session
            user_id: ID of the user
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            List of exercise impact analyses
        """
        # Get exercise events
        result = await session.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.event_type == "exercise",
                ContextEvent.timestamp >= start_date,
                ContextEvent.timestamp <= end_date,
            )
            .order_by(ContextEvent.timestamp)
        )
        
        exercises = result.scalars().all()
        analyses = []
        
        for exercise in exercises:
            exercise_time = exercise.timestamp
            exercise_end = exercise_time + timedelta(minutes=(exercise.duration or 60))
            
            # Get glucose before exercise (baseline)
            baseline_start = exercise_time - timedelta(hours=2)
            baseline_end = exercise_time
            
            baseline_result = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= baseline_start,
                    GlucoseReading.timestamp < baseline_end,
                )
                .order_by(GlucoseReading.timestamp)
            )
            
            baseline_readings = baseline_result.scalars().all()
            
            # Get glucose during and after exercise
            post_start = exercise_time
            post_end = exercise_time + timedelta(hours=self.EXERCISE_WINDOW)
            
            post_result = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= post_start,
                    GlucoseReading.timestamp <= post_end,
                )
                .order_by(GlucoseReading.timestamp)
            )
            
            post_readings = post_result.scalars().all()
            
            if not baseline_readings or not post_readings:
                continue
            
            # Calculate baseline average
            baseline_avg = statistics.mean([r.glucose_value for r in baseline_readings])
            
            # Calculate post-exercise metrics
            post_values = [r.glucose_value for r in post_readings]
            post_avg = statistics.mean(post_values)
            post_min = min(post_values)
            post_max = max(post_values)
            
            # Find lowest point (likely during/after exercise)
            min_reading = min(post_readings, key=lambda r: r.glucose_value)
            
            # Calculate change from baseline
            change_from_baseline = post_avg - baseline_avg
            min_drop = post_min - baseline_avg
            
            # Determine impact type
            impact_type = self._classify_exercise_impact(
                baseline_avg, post_avg, post_min, exercise.intensity
            )
            
            analyses.append({
                "exercise": {
                    "timestamp": exercise.timestamp,
                    "duration_minutes": exercise.duration or 0,
                    "intensity": exercise.intensity or "unknown",
                    "heart_rate_avg": exercise.heart_rate_avg,
                },
                "baseline": {
                    "average": round(baseline_avg, 1),
                    "time_window": "2 hours before exercise",
                },
                "post_exercise": {
                    "average": round(post_avg, 1),
                    "minimum": round(post_min, 1),
                    "minimum_time": min_reading.timestamp,
                    "maximum": round(post_max, 1),
                    "hours_monitored": self.EXERCISE_WINDOW,
                },
                "impact": {
                    "type": impact_type,
                    "avg_change_from_baseline": round(change_from_baseline, 1),
                    "min_drop_from_baseline": round(min_drop, 1),
                    "hypoglycemia_risk": min_reading.glucose_value < self.HYPO_THRESHOLD,
                },
                "recommendations": self._generate_exercise_recommendations(
                    impact_type, min_drop, exercise.intensity
                ),
            })
        
        return analyses
    
    def _classify_exercise_impact(
        self,
        baseline: float,
        post_avg: float,
        post_min: float,
        intensity: Optional[str],
    ) -> str:
        """Classify the type of exercise impact on glucose.
        
        Args:
            baseline: Pre-exercise glucose (mg/dL)
            post_avg: Post-exercise average glucose (mg/dL)
            post_min: Post-exercise minimum glucose (mg/dL)
            intensity: Exercise intensity
            
        Returns:
            Impact classification
        """
        if post_min < self.HYPO_THRESHOLD:
            return "hypoglycemia_risk"
        if post_avg < baseline - 30:
            return "significant_drop"
        if post_avg < baseline - 15:
            return "moderate_drop"
        if intensity == "high" and baseline > self.HYPER_THRESHOLD:
            # High intensity can sometimes raise glucose initially
            if post_avg > baseline:
                return "glucose_rise"
        return "stable_or_mild_drop"
    
    def _generate_exercise_recommendations(
        self,
        impact_type: str,
        glucose_drop: float,
        intensity: Optional[str],
    ) -> List[str]:
        """Generate exercise recommendations.
        
        Args:
            impact_type: Type of exercise impact
            glucose_drop: Glucose decrease (mg/dL)
            intensity: Exercise intensity
            
        Returns:
            List of recommendations
        """
        recs = []
        
        if impact_type == "hypoglycemia_risk":
            recs.append("High hypoglycemia risk during exercise")
            recs.append("Reduce basal insulin before exercise")
            recs.append("Carry fast-acting glucose during exercise")
        
        if impact_type in ["significant_drop", "hypoglycemia_risk"]:
            recs.append("Consider reducing rapid insulin 1-2 hours before exercise")
            recs.append("Eat 15-30g carbs before and during prolonged exercise")
        
        if intensity == "high" and impact_type not in ["hypoglycemia_risk", "significant_drop"]:
            recs.append("Monitor for delayed hypoglycemia up to 24 hours post-exercise")
        
        if impact_type == "glucose_rise":
            recs.append("High-intensity exercise can raise glucose initially")
            recs.append("Monitor closely for delayed drop in following hours")
        
        recs.append("Check glucose before, during (if prolonged), and after exercise")
        recs.append("Reduce correction factor insulin on active days")
        
        return recs


# ---------------------------------------------------------------------------
# Delayed High-Fat Meal Detection
# ---------------------------------------------------------------------------

    async def detect_delayed_high_fat_effects(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        fat_threshold: float = 25,  # grams
        delay_hours: int = 4,
    ) -> List[Dict[str, Any]]:
        """Detect delayed glucose rises from high-fat meals.
        
        High-fat meals can cause delayed glucose spikes several hours
        after eating due to slower gastric emptying.
        
        Args:
            session: Database session
            user_id: ID of the user
            start_date: Start of analysis period
            end_date: End of analysis period
            fat_threshold: Minimum fat grams to consider
            delay_hours: Hours after meal to check for delayed spike
            
        Returns:
            List of delayed high-fat meal effects
        """
        # Get high-fat meals
        result = await session.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.event_type == "meal",
                ContextEvent.timestamp >= start_date,
                ContextEvent.timestamp <= end_date,
                ContextEvent.fat_grams >= fat_threshold,
            )
            .order_by(ContextEvent.timestamp)
        )
        
        high_fat_meals = result.scalars().all()
        delayed_effects = []
        
        for event in high_fat_meals:
            # Check for glucose rise in delayed window
            window_start = event.timestamp + timedelta(hours=delay_hours)
            window_end = event.timestamp + timedelta(hours=delay_hours + 3)
            
            pre_meal_readings = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= event.timestamp,
                    GlucoseReading.timestamp < window_start,
                )
                .order_by(GlucoseReading.timestamp.desc())
            )
            
            pre_meal = pre_meal_readings.scalars().first()
            
            delayed_readings = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= window_start,
                    GlucoseReading.timestamp <= window_end,
                )
                .order_by(GlucoseReading.timestamp)
            )
            
            delayed = delayed_readings.scalars().all()
            
            if not pre_meal or not delayed:
                continue
            
            # Find peak in delayed window
            peak = max(delayed, key=lambda r: r.glucose_value)
            delay_rise = peak.glucose_value - pre_meal.glucose_value
            
            # Check if this is a significant delayed rise
            if delay_rise >= 30 and peak.glucose_value > self.TIR_HIGH:
                hours_to_peak = (peak.timestamp - event.timestamp).total_seconds() / 3600
                
                delayed_effects.append({
                    "meal": {
                        "timestamp": event.timestamp,
                        "carbs": event.carbs_grams,
                        "fat": event.fat_grams,
                        "protein": event.protein_grams,
                        "calories": event.calories,
                    },
                    "pre_meal_glucose": round(pre_meal.glucose_value, 1),
                    "peak_glucose": round(peak.glucose_value, 1),
                    "delayed_rise": round(delay_rise, 1),
                    "hours_to_peak": round(hours_to_peak, 1),
                    "severity": self._classify_spike_severity(delay_rise, peak.glucose_value),
                    "recommendations": [
                        "High-fat meals can cause delayed glucose rises",
                        "Consider extended or combination bolus for high-fat meals",
                        "Monitor glucose for 6-8 hours after high-fat meals",
                        "Split high-fat meals into smaller portions",
                    ],
                })
        
        return delayed_effects


# ---------------------------------------------------------------------------
# Correlation Analysis
# ---------------------------------------------------------------------------

    async def analyze_correlations(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[PatternCorrelation]:
        """Analyze correlations between glucose patterns and lifestyle events.
        
        Args:
            session: Database session
            user_id: ID of the user
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            List of correlations with strength
        """
        correlations = []
        
        # Get all events in period
        events_result = await session.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.timestamp >= start_date,
                ContextEvent.timestamp <= end_date,
            )
            .order_by(ContextEvent.timestamp)
        )
        
        events = events_result.scalars().all()
        
        # Group events by type
        meals = [e for e in events if e.event_type == "meal"]
        exercise_events = [e for e in events if e.event_type == "exercise"]
        insulin_events = [e for e in events if e.event_type == "insulin"]
        
        # Analyze meal impact on glucose
        if meals:
            meal_corr = await self._analyze_meal_correlation(
                session, user_id, meals, start_date, end_date
            )
            if meal_corr:
                correlations.append(meal_corr)
        
        # Analyze exercise impact
        if exercise_events:
            exercise_corr = await self._analyze_exercise_correlation(
                session, user_id, exercise_events, start_date, end_date
            )
            if exercise_corr:
                correlations.append(exercise_corr)
        
        return correlations
    
    async def _analyze_meal_correlation(
        self,
        session: AsyncSession,
        user_id: int,
        meals: List[ContextEvent],
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[PatternCorrelation]:
        """Analyze correlation between meals and glucose spikes."""
        total_meals = len(meals)
        spike_count = 0
        
        for meal in meals:
            # Check for spike within 2 hours
            window_end = meal.timestamp + timedelta(hours=2)
            
            readings = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= meal.timestamp,
                    GlucoseReading.timestamp <= window_end,
                    GlucoseReading.glucose_value > self.HYPER_THRESHOLD,
                )
            )
            
            if readings.scalars().first():
                spike_count += 1
        
        if total_meals > 0:
            correlation_strength = spike_count / total_meals
            return PatternCorrelation(
                event_type="meal",
                correlation_strength=correlation_strength,
            )
        
        return None
    
    async def _analyze_exercise_correlation(
        self,
        session: AsyncSession,
        user_id: int,
        exercise_events: List[ContextEvent],
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[PatternCorrelation]:
        """Analyze correlation between exercise and glucose drops."""
        total_exercises = len(exercise_events)
        drop_count = 0
        
        for exercise in exercise_events:
            # Check for drop within 4 hours after
            window_end = exercise.timestamp + timedelta(hours=4)
            
            readings = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= exercise.timestamp,
                    GlucoseReading.timestamp <= window_end,
                    GlucoseReading.glucose_value < self.HYPO_THRESHOLD,
                )
            )
            
            if readings.scalars().first():
                drop_count += 1
        
        if total_exercises > 0:
            correlation_strength = drop_count / total_exercises
            return PatternCorrelation(
                event_type="exercise",
                correlation_strength=round(correlation_strength, 2),
            )
        
        return None


# ---------------------------------------------------------------------------
# Pattern Detection
# ---------------------------------------------------------------------------

    async def detect_patterns(
        self,
        session: AsyncSession,
        detection_request: PatternDetectionRequest,
    ) -> PatternDetectionResponse:
        """Detect specified patterns in glucose data.
        
        Args:
            session: Database session
            detection_request: Pattern detection request
            
        Returns:
            Pattern detection response
        """
        # Get user from first detection request (all same user)
        # This is a simplification - in production, pass user_id explicitly
        raise NotImplementedError("Full pattern detection to be implemented")


# ---------------------------------------------------------------------------
# Statistical Summaries
# ---------------------------------------------------------------------------

    async def generate_statistical_summary(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        period: str = "weekly",  # daily, weekly, monthly
    ) -> Dict[str, Any]:
        """Generate statistical summary for a time period.
        
        Args:
            session: Database session
            user_id: ID of the user
            start_date: Start of period
            end_date: End of period
            period: Summary period (daily, weekly, monthly)
            
        Returns:
            Statistical summary
        """
        # Calculate TIR
        tir_result = await self.calculate_time_in_range(
            session, user_id, start_date, end_date
        )
        
        # Detect post-meal spikes
        spikes = await self.detect_post_meal_spikes(
            session, user_id, start_date, end_date
        )
        
        # Detect overnight hypoglycemia
        overnight = await self.detect_overnight_hypoglycemia(
            session, user_id, start_date, end_date
        )
        
        # Analyze exercise impact
        exercise_impacts = await self.analyze_exercise_impact(
            session, user_id, start_date, end_date
        )
        
        # Analyze correlations
        correlations = await self.analyze_correlations(
            session, user_id, start_date, end_date
        )
        
        return {
            "period": period,
            "date_range": {
                "start": start_date,
                "end": end_date,
            },
            "tir_analysis": tir_result,
            "post_meal_spikes": {
                "count": len(spikes),
                "spikes": spikes[:5],  # Top 5
            },
            "overnight_hypoglycemia": {
                "event_count": len(overnight),
                "events": overnight[:5],  # Top 5
            },
            "exercise_impact": {
                "sessions_analyzed": len(exercise_impacts),
                "impacts": exercise_impacts[:5],  # Top 5
            },
            "correlations": [c.model_dump() for c in correlations],
        }