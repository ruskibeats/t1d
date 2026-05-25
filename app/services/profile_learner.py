"""Profile Learning Convergence Service.

Matches a user's actual glucose data to the 12 anchor profiles (or hybrid)
after 2+ weeks of data collection. This is the core personalization feature.

Approach:
1. Compute user metrics from their actual glucose readings + context events
2. Score each anchor by how closely the user's metrics match the anchor's parameter ranges
3. Return top N matches with hybrid weights

Per the knowledge base:
- "System attempts to match user's data to closest profile(s)"
- "Hybrid profiles created when no single anchor fits"
- "60% post_meal_spike, 30% dawn_phenomenon, 10% well_controlled"
- "2-week calibration — minimum data for profile learning"
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.simulator.schemas import AnchorType
from app.simulator.anchors import ANCHOR_PARAMETER_RANGES

logger = logging.getLogger(__name__)


# ── Config ──

_MIN_DAYS_FOR_LEARNING = 7       # usable but low confidence
_TARGET_DAYS_FOR_LEARNING = 14   # full confidence
_MIN_READINGS_PER_DAY = 48       # ~4 per hour minimum to be useful


# ── Data types ──


@dataclass
class UserGlucoseStats:
    """Computed glucose statistics from real user data."""
    total_readings: int = 0
    days_of_data: float = 0.0
    avg_glucose_mgdl: float = 110.0
    glucose_std_dev: float = 20.0
    tir_percentage: float = 60.0
    hypo_rate: float = 0.05       # fraction of readings below 70
    severe_hypo_rate: float = 0.01
    hyper_rate: float = 0.20      # fraction above 180
    variability_cv: float = 25.0  # coefficient of variation (%)
    meal_spike_avg_mgdl: float = 40.0  # avg post-meal rise
    overnight_low_rate: float = 0.05   # fraction of overnight readings low
    dawn_trend_mgdl_per_hour: float = 0.0  # glucose rise rate in morning
    exercise_drop_pct: float = 15.0  # avg % drop after exercise
    estimated_a1c: float = 6.5


@dataclass
class AnchorMatch:
    """A single anchor profile match with score."""
    anchor_type: str
    label: str
    description: str
    score: float  # 0.0-1.0, higher = better match
    confidence: float  # how much data we had (0.0-1.0)


@dataclass
class ProfileLearningResult:
    """Result of profile learning convergence."""
    days_of_data: float
    confidence: str  # low, moderate, high (based on data volume)
    primary_anchor: Optional[AnchorMatch] = None
    top_matches: List[AnchorMatch] = field(default_factory=list)
    hybrid_weights: Dict[str, float] = field(default_factory=dict)
    is_ready: bool = False


# ── Anchor fingerprint definitions ──

_ANCHOR_FINGERPRINTS: Dict[str, Dict[str, Tuple[float, float]]] = {}

for at, params in ANCHOR_PARAMETER_RANGES.items():
    _ANCHOR_FINGERPRINTS[at.value] = {
        "basal_glucose_mean": params.basal_glucose_mean,
        "basal_glucose_amplitude": params.basal_glucose_amplitude,
        "meal_rise_factor": params.meal_rise_factor,
        "insulin_sensitivity": params.insulin_sensitivity,
        "carb_ratio": params.carb_ratio,
        "hypo_risk": params.hypo_risk,
        "noise_sd": params.noise_sd,
        "exercise_drop_factor": params.exercise_drop_factor,
        "dawn_effect_strength": params.dawn_effect_strength,
        "fat_delay_hours": params.fat_delay_hours,
        "variability_cv": params.variability_cv,
    }


# ── Scoring helpers ──


def _value_in_range(value: float, rng: Tuple[float, float]) -> float:
    """Score how well a value falls within a range (0.0-1.0).

    1.0 = value is inside the range
    0.0 = value is far outside
    Linear decay outside range boundaries.
    """
    low, high = rng
    span = high - low
    if span <= 0:
        return 1.0 if value == low else 0.0
    half_span = span * 1.5  # allow 50% grace outside range
    if low <= value <= high:
        return 1.0
    if value < low:
        dist = (low - value) / half_span
        return max(0.0, 1.0 - dist)
    else:
        dist = (value - high) / half_span
        return max(0.0, 1.0 - dist)


def _compute_anchor_scores(
    user_stats: UserGlucoseStats,
) -> List[Tuple[AnchorType, float]]:
    """Score every anchor against user stats.

    Returns list of (anchor_type, score) sorted best-first.
    """
    scores: List[Tuple[str, float]] = []

    for at_key, fingerprint in _ANCHOR_FINGERPRINTS.items():
        dim_scores = []

        # Variability / CV
        dim_scores.append(_value_in_range(user_stats.variability_cv, fingerprint["variability_cv"]))

        # Hypo risk
        hypo_pct = user_stats.hypo_rate * 100
        hypo_range = (
            fingerprint["hypo_risk"][0] * 100,
            fingerprint["hypo_risk"][1] * 100,
        )
        dim_scores.append(_value_in_range(hypo_pct, hypo_range))

        # Basal glucose
        dim_scores.append(_value_in_range(user_stats.avg_glucose_mgdl, fingerprint["basal_glucose_mean"]))

        # Glucose amplitude (std dev as proxy)
        dim_scores.append(_value_in_range(user_stats.glucose_std_dev, fingerprint["basal_glucose_amplitude"]))

        # Dawn effect - match against dawn strength
        dim_scores.append(_value_in_range(
            user_stats.dawn_trend_mgdl_per_hour * 10,  # scale to match dawn_effect_strength range
            fingerprint["dawn_effect_strength"],
        ))

        # Exercise sensitivity - match drop factor
        dim_scores.append(_value_in_range(
            user_stats.exercise_drop_pct,
            fingerprint["exercise_drop_factor"],
        ))

        # Overnight hypo rate against hypo_risk (proxy)
        dim_scores.append(_value_in_range(
            user_stats.overnight_low_rate * 100,
            (fingerprint["hypo_risk"][0] * 50, fingerprint["hypo_risk"][1] * 50),
        ))

        # Overall score = weighted average of dimension scores
        weights = [0.20, 0.15, 0.15, 0.10, 0.15, 0.10, 0.15]
        weighted = sum(s * w for s, w in zip(dim_scores, weights))
        total_w = sum(weights)
        overall = weighted / total_w if total_w > 0 else 0.0

        scores.append((at_key, overall))

    scores.sort(key=lambda x: -x[1])
    return scores


def _label_for(at_key: str) -> str:
    """Get human-readable label for an anchor type key."""
    labels = {
        "well_controlled": "Well Controlled",
        "brittle": "Brittle / Erratic",
        "dawn_phenomenon": "Dawn Phenomenon",
        "post_meal_spike": "Post-Meal Spike",
        "overnight_hypo": "Overnight Hypo",
        "exercise_sensitive": "Exercise Sensitive",
        "high_fat_delayed": "High Fat Delayed",
        "insulin_sensitive": "Insulin Sensitive",
        "insulin_resistant": "Insulin Resistant",
        "high_variability": "High Variability",
        "exercise_regimen": "Exercise Regimen",
        "newly_diagnosed": "Newly Diagnosed",
    }
    return labels.get(at_key, at_key.replace("_", " ").title())


# ── Public API ──


def compute_profile_match(
    user_stats: UserGlucoseStats,
) -> ProfileLearningResult:
    """Compute profile match from user glucose statistics.

    Args:
        user_stats: Computed statistics from real user glucose data.

    Returns:
        ProfileLearningResult with primary anchor, top matches, and hybrid weights.
    """
    days = user_stats.days_of_data
    readings_per_day = user_stats.total_readings / max(days, 1)

    # Determine data sufficiency
    if days < _MIN_DAYS_FOR_LEARNING or readings_per_day < _MIN_READINGS_PER_DAY:
        data_confidence = "low"
        is_ready = False
    elif days >= _TARGET_DAYS_FOR_LEARNING and readings_per_day >= _MIN_READINGS_PER_DAY * 2:
        data_confidence = "high"
        is_ready = True
    else:
        data_confidence = "moderate"
        is_ready = days >= _MIN_DAYS_FOR_LEARNING

    # Score anchors
    scored = _compute_anchor_scores(user_stats)

    # Build matches
    matches = []
    for at_key, score in scored:
        matches.append(AnchorMatch(
            anchor_type=at_key,
            label=_label_for(at_key),
            description=at_key.replace("_", " ").title(),
            score=round(score, 3),
            confidence=1.0 if is_ready else max(0.3, days / _TARGET_DAYS_FOR_LEARNING),
        ))

    # Best match
    primary = matches[0] if matches else None

    # Hybrid weights: normalize top 3 scores to sum to 1.0
    hybrid = {}
    top3 = scored[:3]
    total_score = sum(s for _, s in top3) or 1.0
    for at_key, s in top3:
        if s > 0:
            hybrid[at_key] = round(s / total_score, 3)

    return ProfileLearningResult(
        days_of_data=round(days, 1),
        confidence=data_confidence,
        primary_anchor=primary,
        top_matches=matches[:5],
        hybrid_weights=hybrid,
        is_ready=is_ready,
    )


def compute_from_readings(
    glucose_readings: List[Dict[str, Any]],
    meal_events: Optional[List[Dict[str, Any]]] = None,
    exercise_events: Optional[List[Dict[str, Any]]] = None,
) -> ProfileLearningResult:
    """Compute profile match directly from glucose readings and events.

    This is the main entry point for production use. Takes raw user data
    and extracts the UserGlucoseStats needed for profile matching.

    Args:
        glucose_readings: List of dicts with 'timestamp' and 'glucose_value' keys.
        meal_events: Optional list of meal events with 'timestamp' and 'carbs_grams'.
        exercise_events: Optional list of exercise events with 'timestamp'.

    Returns:
        ProfileLearningResult with matched profile(s).
    """
    if not glucose_readings:
        return ProfileLearningResult(
            days_of_data=0,
            confidence="low",
            is_ready=False,
        )

    # Compute basic stats
    values = [float(r.get("glucose_value", r.get("value", 0))) for r in glucose_readings]
    values = [v for v in values if v > 0]
    if not values:
        return ProfileLearningResult(days_of_data=0, confidence="low", is_ready=False)

    timestamps = [r.get("timestamp") for r in glucose_readings if r.get("timestamp")]
    if timestamps:
        try:
            ts_list = [datetime.fromisoformat(t) if isinstance(t, str) else t for t in timestamps]
            days = (max(ts_list) - min(ts_list)).total_seconds() / 86400
        except (ValueError, TypeError):
            days = len(glucose_readings) / 288  # assume 5-min CGM
    else:
        days = len(glucose_readings) / 288

    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std_dev = variance ** 0.5
    cv = (std_dev / mean * 100) if mean > 0 else 0

    below_70 = sum(1 for v in values if v < 70)
    below_54 = sum(1 for v in values if v < 54)
    above_180 = sum(1 for v in values if v > 180)
    in_range = n - below_70 - above_180

    hypo_rate = below_70 / n
    severe_hypo_rate = below_54 / n
    hyper_rate = above_180 / n
    tir_pct = (in_range / n * 100) if n > 0 else 0
    estimated_a1c = round((mean + 46.7) / 28.7, 1) if mean else 0

    # Dawn trend: compare avg glucose in early morning (5-9am) vs overnight (12-5am)
    dawn_trend = 0.0
    if timestamps:
        morning_readings = []
        night_readings = []
        for r in glucose_readings:
            ts = r.get("timestamp")
            if ts:
                try:
                    t = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
                    h = t.hour
                    v = float(r.get("glucose_value", r.get("value", 0)))
                    if 5 <= h <= 9:
                        morning_readings.append(v)
                    elif 0 <= h <= 4:
                        night_readings.append(v)
                except (ValueError, TypeError):
                    pass
        if morning_readings and night_readings:
            morning_avg = sum(morning_readings) / len(morning_readings)
            night_avg = sum(night_readings) / len(night_readings)
            dawn_trend = morning_avg - night_avg  # positive = dawn phenomenon

    # Overnight low rate (12am-6am)
    overnight_low_rate = 0.0
    overnight_readings = 0
    overnight_lows = 0
    for r in glucose_readings:
        ts = r.get("timestamp")
        if ts:
            try:
                t = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
                if 0 <= t.hour <= 6:
                    overnight_readings += 1
                    if float(r.get("glucose_value", r.get("value", 0))) < 70:
                        overnight_lows += 1
            except (ValueError, TypeError):
                pass
    if overnight_readings > 0:
        overnight_low_rate = overnight_lows / overnight_readings

    # Meal spike analysis (if meal events provided)
    meal_spike_avg = 40.0  # default
    if meal_events and timestamps:
        spikes = []
        for meal in meal_events:
            meal_ts = meal.get("timestamp")
            if not meal_ts:
                continue
            try:
                mt = datetime.fromisoformat(meal_ts) if isinstance(meal_ts, str) else meal_ts
                # Find glucose 60-120 min after meal
                after_readings = []
                for r in glucose_readings:
                    rt = r.get("timestamp")
                    if rt:
                        try:
                            rt_dt = datetime.fromisoformat(rt) if isinstance(rt, str) else rt
                            delta = (rt_dt - mt).total_seconds() / 60
                            if 60 <= delta <= 120:
                                after_readings.append(float(r.get("glucose_value", r.get("value", 0))))
                        except (ValueError, TypeError):
                            pass
                if after_readings and len(after_readings) >= 2:
                    pre_value = float(meal.get("pre_meal_glucose", meal.get("glucose_before", mean)))
                    peak = max(after_readings)
                    spikes.append(peak - pre_value)
            except (ValueError, TypeError):
                pass
        if spikes:
            meal_spike_avg = sum(spikes) / len(spikes)

    # Exercise sensitivity (if exercise events provided)
    exercise_drop_pct = 15.0  # default
    if exercise_events and timestamps:
        drops = []
        for ex in exercise_events:
            ex_ts = ex.get("timestamp")
            if not ex_ts:
                continue
            try:
                et = datetime.fromisoformat(ex_ts) if isinstance(ex_ts, str) else ex_ts
                # Find glucose 30-90 min after exercise
                before = []
                after = []
                for r in glucose_readings:
                    rt = r.get("timestamp")
                    if rt:
                        try:
                            rt_dt = datetime.fromisoformat(rt) if isinstance(rt, str) else rt
                            delta = (rt_dt - et).total_seconds() / 60
                            if -30 <= delta <= 0:
                                before.append(float(r.get("glucose_value", r.get("value", 0))))
                            elif 30 <= delta <= 90:
                                after.append(float(r.get("glucose_value", r.get("value", 0))))
                        except (ValueError, TypeError):
                            pass
                if before and after:
                    pre_avg = sum(before) / len(before)
                    post_avg = sum(after) / len(after)
                    if pre_avg > 0:
                        drop_pct = (pre_avg - post_avg) / pre_avg * 100
                        if drop_pct > 0:
                            drops.append(drop_pct)
            except (ValueError, TypeError):
                pass
        if drops:
            exercise_drop_pct = sum(drops) / len(drops)

    stats = UserGlucoseStats(
        total_readings=n,
        days_of_data=days,
        avg_glucose_mgdl=round(mean, 1),
        glucose_std_dev=round(std_dev, 1),
        tir_percentage=round(tir_pct, 1),
        hypo_rate=round(hypo_rate, 3),
        severe_hypo_rate=round(severe_hypo_rate, 3),
        hyper_rate=round(hyper_rate, 3),
        variability_cv=round(cv, 1),
        meal_spike_avg_mgdl=round(meal_spike_avg, 1),
        overnight_low_rate=round(overnight_low_rate, 3),
        dawn_trend_mgdl_per_hour=round(dawn_trend, 1),
        exercise_drop_pct=round(exercise_drop_pct, 1),
        estimated_a1c=estimated_a1c,
    )

    return compute_profile_match(stats)