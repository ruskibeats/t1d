"""Outcome evaluator for comparing forecast vs observed post-meal glucose.

Measures whether forecasted timing, rise risk, and confidence match
observed post-meal glucose behavior.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

from app.services.meal_forecast_engine import MealForecast, RiskLevel


@dataclass
class PostMealGlucoseObservation:
    """Observed glucose data after a meal."""
    meal_time: datetime
    glucose_readings: List[tuple[float, datetime]]  # (value, timestamp)


@dataclass
class EvaluationWindow:
    """Evaluation window definition."""
    name: str
    start_minutes: int
    end_minutes: int


@dataclass
class OutcomeMetrics:
    """Metrics comparing forecast to observed outcome."""
    forecast: MealForecast
    meal_time: datetime
    
    # Timing accuracy
    predicted_onset_window: EvaluationWindow
    observed_rise_time: Optional[float]  # minutes after meal, or None
    timing_accuracy: float  # 0.0 to 1.0
    
    # Risk calibration
    predicted_risk: RiskLevel
    observed_risk: RiskLevel
    risk_calibrated: bool
    
    # Rise detection
    rise_detected: bool
    peak_magnitude: float  # mg/dL
    delay_present: bool


EVALUATION_WINDOWS = [
    EvaluationWindow("early", 0, 60),
    EvaluationWindow("mid", 60, 120),
    EvaluationWindow("late", 120, 240),
]


def evaluate_forecast_outcome(
    forecast: MealForecast,
    observation: PostMealGlucoseObservation,
    baseline_glucose: float,
) -> OutcomeMetrics:
    """Evaluate forecast against observed outcomes.
    
    Args:
        forecast: Original meal forecast
        observation: Observed glucose readings
        baseline_glucose: Glucose at meal time
        
    Returns:
        OutcomeMetrics with evaluation results
    """
    # Analyze glucose trajectory
    readings = sorted(observation.glucose_readings, key=lambda x: x[1])
    
    meal_time = observation.meal_time
    
    # Find rise timing
    rise_start = None
    peak_value = baseline_glucose
    peak_time = None
    
    for value, timestamp in readings:
        minutes_after = (timestamp - meal_time).total_seconds() / 60
        
        if value > baseline_glucose + 20 and rise_start is None:
            rise_start = minutes_after
        
        if value > peak_value:
            peak_value = value
            peak_time = minutes_after
    
    # Determine observed risk
    peak_magnitude = peak_value - baseline_glucose
    
    if peak_magnitude < 30:
        observed_risk = RiskLevel.LOW
    elif peak_magnitude < 60:
        observed_risk = RiskLevel.MODERATE
    else:
        observed_risk = RiskLevel.HIGH
    
    # Check for delay
    delay_present = peak_time and peak_time > 120
    
    # Timing accuracy (how close predicted onset was to observed)
    predicted_onset_min = forecast.timing_onset_window.earliest_minutes
    predicted_onset_max = forecast.timing_onset_window.latest_minutes
    
    if rise_start:
        if predicted_onset_min <= rise_start <= predicted_onset_max:
            timing_accuracy = 1.0
        else:
            timing_accuracy = max(0.0, 1.0 - abs(rise_start - (predicted_onset_min + predicted_onset_max) / 2) / 60)
    else:
        timing_accuracy = 0.0
    
    # Risk calibration
    risk_calibrated = forecast.risk_level == observed_risk
    
    return OutcomeMetrics(
        forecast=forecast,
        meal_time=meal_time,
        predicted_onset_window=EvaluationWindow(
            "predicted",
            forecast.timing_onset_window.earliest_minutes,
            forecast.timing_onset_window.latest_minutes,
        ),
        observed_rise_time=rise_start,
        timing_accuracy=timing_accuracy,
        predicted_risk=forecast.risk_level,
        observed_risk=observed_risk,
        risk_calibrated=risk_calibrated,
        rise_detected=rise_start is not None,
        peak_magnitude=peak_magnitude,
        delay_present=delay_present,
    )


def compute_cohort_metrics(evaluations: List[OutcomeMetrics]) -> dict:
    """Compute cohort-level metrics.
    
    Args:
        evaluations: List of outcome evaluations
        
    Returns:
        Dictionary of aggregate metrics
    """
    if not evaluations:
        return {"count": 0}
    
    total = len(evaluations)
    calibrated = sum(1 for e in evaluations if e.risk_calibrated)
    timing_accurate = sum(1 for e in evaluations if e.timing_accuracy >= 0.5)
    rise_detected = sum(1 for e in evaluations if e.rise_detected)
    
    return {
        "count": total,
        "calibration_rate": calibrated / total,
        "timing_accuracy_rate": timing_accurate / total,
        "rise_detection_rate": rise_detected / total,
        "avg_timing_accuracy": sum(e.timing_accuracy for e in evaluations) / total,
    }