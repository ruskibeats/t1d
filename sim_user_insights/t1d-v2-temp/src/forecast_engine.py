#!/usr/bin/env python3
"""Forecast engine — functional pipeline (Design B).

Each kernel is an independently testable pure function.
Compose them in `forecast_glucose()`.
No I/O, no async, no DB. Only deterministic math.
"""

from __future__ import annotations

import math
from functools import lru_cache
from dataclasses import dataclass, field
from typing import Any, Callable

from demo.physiology_model import (
    PhysiologyForecastModel,
    PhysiologyParameters,
)

# ── Data types ──

@dataclass
class MealTotals:
    carbs_g: float = 0.0
    fat_g: float = 0.0
    sugars_g: float = 0.0
    protein_g: float = 0.0
    kcal: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> MealTotals:
        return cls(
            carbs_g=d.get("carbs_g", 0),
            fat_g=d.get("fat_g", 0),
            sugars_g=d.get("sugars_g", 0),
            protein_g=d.get("protein_g", 0),
            kcal=d.get("kcal", 0),
        )


@dataclass
class ForecastPoint:
    hour: int
    glucose_mg_dl: int


@dataclass
class NighttimePoint:
    time: str
    hours_after_meal: int
    glucose_mg_dl: int
    note: str = ""


@dataclass
class ForecastScenario:
    """One forecast scenario within a carb uncertainty band."""
    label: str
    carbs_g: float
    peak_mg_dl: int
    peak_time_minutes: int
    forecast_points: list[ForecastPoint] = field(default_factory=list)


@dataclass
class ForecastUncertaintyBand:
    """Low/point/high forecasts induced by carb-estimation uncertainty."""
    low: ForecastScenario
    point: ForecastScenario
    high: ForecastScenario
    peak_range_mg_dl: tuple[int, int]
    peak_time_range_minutes: tuple[int, int]


@dataclass
class ForecastResult:
    baseline_mg_dl: int
    peak_mg_dl: int
    peak_time_minutes: int
    forecast_points: list[ForecastPoint] = field(default_factory=list)
    nighttime: list[NighttimePoint] = field(default_factory=list)
    exercise_heat_modifier: float = 1.0
    meal_drivers: dict[str, Any] = field(default_factory=dict)
    uncertainty_band: ForecastUncertaintyBand | None = None

    # Evidence/provenance fields (Phase 2 guardrails)
    top_drivers: list[str] = field(default_factory=list)
    historical_similarity_score: float | None = None
    profile_assumptions: dict[str, Any] = field(default_factory=dict)
    missing_information_flags: list[str] = field(default_factory=list)
    evidence_items: list[dict] = field(default_factory=list)


# ── Calibration maps ──

RISE_PER_CARB_MAP: dict[str, float] = {
    # Companion-facing effective mg/dL rise per gram before insulin/action
    # compartments. These are intentionally below the full simulator's raw
    # meal_rise_factor values but high enough to match simulated historical
    # meal deltas (typically ~40-90 mg/dL for 40-80g meals).
    "well_controlled": 1.5, "high_fat_delayed": 3.0,
    "post_meal_spike": 3.0, "brittle": 2.8,
    "dawn_phenomenon": 1.7, "overnight_hypo": 1.4,
    "exercise_sensitive": 1.5, "exercise_regimen": 1.4,
    "insulin_sensitive": 1.3, "insulin_resistant": 2.5,
    "high_variability": 2.6, "newly_diagnosed": 2.8,
}

BALANCE_MAP: dict[str, float] = {
    "well_controlled": 1.2, "high_fat_delayed": 1.35,
    "post_meal_spike": 2.0, "brittle": 1.8,
    "dawn_phenomenon": 1.0, "overnight_hypo": 1.0,
    "exercise_sensitive": 1.1, "exercise_regimen": 1.0,
    "insulin_sensitive": 1.0, "insulin_resistant": 1.6,
    "high_variability": 1.5, "newly_diagnosed": 1.7,
}


# ── Raw kernels (independently testable) ──

MEAL_WINDOW_STEPS = 36       # 3 hours × 12 five-minute steps
INSULIN_WINDOW_STEPS = 72    # 6 hours × 12 five-minute steps
SLOW_MEAL_PEAK_STEP = 18     # 90 minutes
FAST_SUGAR_PEAK_STEP = 5     # 25 minutes
FAST_SUGAR_WINDOW_STEPS = 18 # 90 minutes
INSULIN_PEAK_STEP = 18       # 90 minutes, aligned with simulator
DRIFT_RATE_PER_STEP = 0.015  # OU mean reversion per 5-minute step


def soft_glucose_cap(v: float) -> float:
    """Soft physiological boundary, matching the main simulator.

    This avoids hard clipping mass pile-up at 40/400 while keeping values
    in a realistic CGM-like envelope.
    """
    if v > 400.0:
        return 400.0 + 15.0 * (1.0 - math.exp(-(v - 400.0) / 15.0))
    if v < 40.0:
        return 40.0 - 15.0 * (1.0 - math.exp(-(40.0 - v) / 15.0))
    return v


@lru_cache(maxsize=None)
def normalized_gamma_impulse(step: int, peak: int, total: int) -> float:
    """Discrete gamma impulse normalised so sum over the window is 1.0.

    The main simulator uses the same impulse shape. We compute the empirical
    discrete denominator directly instead of relying on an analytical integral,
    because the finite 5-minute grid is what determines event mass.
    """
    if step <= 0 or step > total:
        return 0.0
    denom = sum(s * math.exp(-s / peak) for s in range(1, total + 1))
    if denom <= 0:
        return 0.0
    return step * math.exp(-step / peak) / denom


def project_fast_rise(
    sugars_g: float, rise_per_g: float
) -> float:
    """Total fast-sugar rise distributed by a normalised impulse."""
    return sugars_g * rise_per_g * 1.2


def project_slow_rise(
    carbs_g: float, sugars_g: float, fat_g: float,
    rise_per_g: float, fat_delay_hours: float,
) -> tuple[float, bool, int]:
    """Total starch rise and delayed-tail metadata.

    Returns (slow_rise_mg_dl, has_delayed_tail, tail_start_step). The slow
    rise itself is distributed over the standard 3-hour meal absorption window;
    high-fat meals add a separately normalised delayed tail so the extra mass is
    explicit rather than an unbounded exponential area.
    """
    slow_carbs = max(carbs_g - sugars_g, 0)
    slow_rise = slow_carbs * rise_per_g
    ext_tail = fat_g >= 15
    tail_start_step = MEAL_WINDOW_STEPS + max(
        0, int(round(fat_delay_hours * 12)) - MEAL_WINDOW_STEPS
    )
    return (slow_rise, ext_tail, tail_start_step)


def project_insulin_effect(
    carbs_g: float, carb_ratio: float, insulin_sensitivity: float,
    balance_factor: float,
) -> float:
    """Total insulin glucose-lowering effect distributed over 6 hours.

    Uses the same 0.25 factor as the main simulator, with the anchor balance
    factor controlling excursion size by reducing effective meal insulin for
    spike-prone anchors.
    """
    insulin_units = carbs_g / carb_ratio if carb_ratio else 0
    return insulin_units * insulin_sensitivity * 0.25 / balance_factor


def compute_exercise_heat_modifier(exercise_drop_factor: float) -> float:
    """Compute modifier from profile's exercise drop factor."""
    if exercise_drop_factor <= 1:
        return 1.0
    return 1.0 - (1.0 - 1.0 / exercise_drop_factor) * 0.5


def _scale_totals_to_carbs(totals: MealTotals, target_carbs_g: float) -> MealTotals:
    """Scale carb-linked macros to a low/high carb scenario.

    Fat/protein/kcal are kept fixed enough for timing context; sugars scale with
    total carbs so fast-carb proportion remains stable across the uncertainty
    band.
    """
    current = max(totals.carbs_g, 0.0)
    target = max(target_carbs_g, 0.0)
    if current <= 0:
        return MealTotals(
            carbs_g=target,
            fat_g=totals.fat_g,
            sugars_g=min(totals.sugars_g, target),
            protein_g=totals.protein_g,
            kcal=totals.kcal,
        )
    scale = target / current
    return MealTotals(
        carbs_g=target,
        fat_g=totals.fat_g,
        sugars_g=min(round(totals.sugars_g * scale, 1), target),
        protein_g=totals.protein_g,
        kcal=totals.kcal,
    )


def _scenario_from_result(label: str, carbs_g: float, result: ForecastResult) -> ForecastScenario:
    return ForecastScenario(
        label=label,
        carbs_g=round(carbs_g, 1),
        peak_mg_dl=result.peak_mg_dl,
        peak_time_minutes=result.peak_time_minutes,
        forecast_points=result.forecast_points,
    )


def compute_nighttime(
    trace: dict[int, float], basal: float,
    meal_hour: int, dt: int = 5,
) -> list[NighttimePoint]:
    """Compute nighttime forecast points from a trace simulated to 16 hours."""
    points = []
    for offset in [8, 10, 12, 14, 16]:
        t_min = offset * 60
        nearest = round(t_min / dt) * dt
        if nearest not in trace:
            raise ValueError("nighttime forecast requires trace coverage to 16 hours")
        g = soft_glucose_cap(trace[nearest])
        prev = trace.get(max(0, nearest - 60), g)
        hr = (meal_hour + offset) % 24
        note = "Falling" if g < prev - 10 else ("Rising" if g > prev + 10 else "Stable")
        points.append(NighttimePoint(
            time=f"{hr:02d}:00",
            hours_after_meal=offset,
            glucose_mg_dl=round(g),
            note=note,
        ))
    return points


# ── Orchestration ──

def forecast_glucose(
    totals: MealTotals,
    basal_mg_dl: float,
    carb_ratio: float,
    insulin_sensitivity: float,
    fat_delay_hours: float,
    exercise_drop_factor: float,
    anchor_type: str = "well_controlled",
    *,
    hour: int = 19,
    dt: int = 5,
    carb_range_g: tuple[float, float] | None = None,
    include_uncertainty: bool = True,
) -> ForecastResult:
    """Compose kernels into a full glucose forecast.

    Pure function — no I/O, no async, no DB.
    All parameters are deterministic profile/meal values.

    Args:
        totals: Macronutrient totals for the meal.
        basal_mg_dl: Basal glucose from profile.
        carb_ratio: g carbs per unit insulin.
        insulin_sensitivity: mg/dL drop per unit insulin.
        fat_delay_hours: How many hours fat extends absorption.
        exercise_drop_factor: Profile's exercise sensitivity.
        anchor_type: Anchor type string for calibration maps.
        hour: Hour of day the meal starts.
        dt: Simulation timestep in minutes.

    Returns:
        ForecastResult with peak, points, and nighttime.
    """
    # Resolve calibration constants
    rise_per_g = RISE_PER_CARB_MAP.get(anchor_type, 0.6)
    balance_factor = BALANCE_MAP.get(anchor_type, 1.2)

    heat_mod = compute_exercise_heat_modifier(exercise_drop_factor)
    ext_tail = totals.fat_g >= 15.0
    fast_total = project_fast_rise(totals.sugars_g, rise_per_g) * heat_mod
    slow_total, _, _tail_start_step = project_slow_rise(
        totals.carbs_g, totals.sugars_g, totals.fat_g, rise_per_g, fat_delay_hours,
    )
    slow_total *= heat_mod

    # Simulate with explicit gut, insulin, glucose, renal, and basal-reversion
    # compartments. Trace extends to 16h so nighttime points are based on real
    # simulated state rather than basal fallback.
    timepoints = [1, 2, 3, 4, 6, 8, 10]
    basal = basal_mg_dl
    model = PhysiologyForecastModel(PhysiologyParameters(
        basal_mg_dl=basal_mg_dl,
        rise_per_g=rise_per_g,
        carb_ratio=carb_ratio,
        insulin_sensitivity=insulin_sensitivity,
        balance_factor=balance_factor,
        exercise_heat_modifier=heat_mod,
        fat_delay_hours=fat_delay_hours,
        basal_reversion_per_min=DRIFT_RATE_PER_STEP / dt,
    ))
    physiology_trace = model.simulate(
        carbs_g=totals.carbs_g,
        sugars_g=totals.sugars_g,
        fat_g=totals.fat_g,
        horizon_minutes=16 * 60,
        dt_minutes=dt,
    )
    trace: dict[int, float] = {
        point.minute: point.glucose_mg_dl for point in physiology_trace.points
    }

    # Sample at requested timepoints
    points = [
        ForecastPoint(hour=hr, glucose_mg_dl=round(trace.get(hr * 60, basal)))
        for hr in timepoints
    ]

    # Find peak
    peak_point = physiology_trace.peak
    peak_t = peak_point.minute

    # Nighttime
    nighttime = compute_nighttime(trace, basal, hour, dt)

    # Build top drivers for explainability
    drivers = []
    if totals.sugars_g > 5:
        drivers.append(f"fast_carbs:{totals.sugars_g:.0f}g")
    if totals.carbs_g - totals.sugars_g > 10:
        drivers.append(f"slow_carbs:{totals.carbs_g - totals.sugars_g:.0f}g")
    if totals.fat_g >= 15:
        drivers.append(f"fat_delays:{totals.fat_g:.0f}g")
    if heat_mod < 1.0:
        drivers.append(f"exercise_mod:{heat_mod:.2f}x")
    
    result = ForecastResult(
        baseline_mg_dl=round(basal),
        peak_mg_dl=round(trace[peak_t]),
        peak_time_minutes=peak_t,
        forecast_points=points,
        nighttime=nighttime,
        exercise_heat_modifier=round(heat_mod, 3),
        meal_drivers={
            "fast_carbs_g": round(totals.sugars_g, 1),
            "slow_carbs_g": round(max(totals.carbs_g - totals.sugars_g, 0), 1),
            "fat_triggers_delay": ext_tail,
            "estimated_peak_rise_mg_dl": round(fast_total + slow_total),
            "balance_factor": balance_factor,
        },
        # Evidence fields for interpretability
        top_drivers=drivers,
        historical_similarity_score=None,  # Populated by caller with historical context
    )
    
    # Profile assumptions for transparency
    result.profile_assumptions = {
        "anchor_type": anchor_type,
        "carb_ratio": carb_ratio,
        "insulin_sensitivity": insulin_sensitivity,
        "fat_delay_hours": fat_delay_hours,
    }
    
    # Missing information flags
    if totals.carbs_g == 0:
        result.missing_information_flags.append("no_carbs_detected")

    if include_uncertainty and carb_range_g is not None:
        low_carb, high_carb = carb_range_g
        low_totals = _scale_totals_to_carbs(totals, low_carb)
        high_totals = _scale_totals_to_carbs(totals, high_carb)
        low = forecast_glucose(
            low_totals, basal_mg_dl, carb_ratio, insulin_sensitivity,
            fat_delay_hours, exercise_drop_factor, anchor_type,
            hour=hour, dt=dt, include_uncertainty=False,
        )
        high = forecast_glucose(
            high_totals, basal_mg_dl, carb_ratio, insulin_sensitivity,
            fat_delay_hours, exercise_drop_factor, anchor_type,
            hour=hour, dt=dt, include_uncertainty=False,
        )
        scenarios = [low, result, high]
        result.uncertainty_band = ForecastUncertaintyBand(
            low=_scenario_from_result("low", low_carb, low),
            point=_scenario_from_result("point", totals.carbs_g, result),
            high=_scenario_from_result("high", high_carb, high),
            peak_range_mg_dl=(min(s.peak_mg_dl for s in scenarios), max(s.peak_mg_dl for s in scenarios)),
            peak_time_range_minutes=(
                min(s.peak_time_minutes for s in scenarios),
                max(s.peak_time_minutes for s in scenarios),
            ),
        )

    return result


def make_forecaster(
    basal_mg_dl: float,
    carb_ratio: float,
    insulin_sensitivity: float,
    fat_delay_hours: float,
    exercise_drop_factor: float,
    anchor_type: str,
) -> Callable[[MealTotals, int], ForecastResult]:
    """Bind profile parameters to the functional pipeline. Convenience wrapper.

    Usage:
        forecaster = make_forecaster(119, 13.9, 29.5, 4.1, 1.13, "high_fat_delayed")
        result = forecaster(meal_totals, hour=19)
    """
    def _predict(totals: MealTotals, hour: int = 19) -> ForecastResult:
        return forecast_glucose(
            totals, basal_mg_dl, carb_ratio, insulin_sensitivity,
            fat_delay_hours, exercise_drop_factor, anchor_type, hour=hour,
        )
    return _predict


# ── ForecastStage: deep module encapsulating calibration + forecast ──

class ForecastStage:
    """Encapsulates per-anchor forecast calibration and the forecast pipeline.

    This is a deep module: a small interface (forecast(totals, hour)) hides
    the calibration constants, kernel composition, and OU simulation.

    Usage:
        stage = ForecastStage.from_profile(profile_config)
        result = stage.forecast(meal_totals, hour=19)
    """

    def __init__(
        self,
        anchor_type: str,
        basal_mg_dl: float,
        carb_ratio: float,
        insulin_sensitivity: float,
        fat_delay_hours: float,
        exercise_drop_factor: float,
    ):
        self.anchor_type = anchor_type
        self.basal_mg_dl = basal_mg_dl
        self.carb_ratio = carb_ratio
        self.insulin_sensitivity = insulin_sensitivity
        self.fat_delay_hours = fat_delay_hours
        self.exercise_drop_factor = exercise_drop_factor

        # Resolve calibration constants from anchor type
        self._rise_per_g = RISE_PER_CARB_MAP.get(anchor_type, 0.6)
        self._balance_factor = BALANCE_MAP.get(anchor_type, 1.2)

    @classmethod
    def from_profile(cls, profile_config: Any) -> ForecastStage:
        """Create a ForecastStage from a PatientConfig-like object."""
        return cls(
            anchor_type=profile_config.anchor_type.value,
            basal_mg_dl=profile_config.basal_glucose_mean,
            carb_ratio=profile_config.carb_ratio,
            insulin_sensitivity=profile_config.insulin_sensitivity,
            fat_delay_hours=profile_config.fat_delay_hours,
            exercise_drop_factor=profile_config.exercise_drop_factor,
        )

    def forecast(
        self,
        totals: MealTotals,
        hour: int = 19,
        carb_range_g: tuple[float, float] | None = None,
    ) -> ForecastResult:
        """Run the full glucose forecast for a meal."""
        return forecast_glucose(
            totals=totals,
            basal_mg_dl=self.basal_mg_dl,
            carb_ratio=self.carb_ratio,
            insulin_sensitivity=self.insulin_sensitivity,
            fat_delay_hours=self.fat_delay_hours,
            exercise_drop_factor=self.exercise_drop_factor,
            anchor_type=self.anchor_type,
            hour=hour,
            carb_range_g=carb_range_g,
        )

    @property
    def calibration(self) -> dict:
        """Return the resolved calibration constants for logging/debugging."""
        return {
            "anchor_type": self.anchor_type,
            "rise_per_g": self._rise_per_g,
            "balance_factor": self._balance_factor,
            "basal_mg_dl": self.basal_mg_dl,
            "carb_ratio": self.carb_ratio,
            "insulin_sensitivity": self.insulin_sensitivity,
            "fat_delay_hours": self.fat_delay_hours,
            "exercise_drop_factor": self.exercise_drop_factor,
        }

# ── Evidence helpers (Phase 2) ──

def populate_evidence_fields(
    result: ForecastResult,
    evidence_items: list[dict] | None = None,
    historical_similarity_score: float | None = None,
    missing_info: list[str] | None = None,
    calibration: dict | None = None,
    overwrite_drivers: bool = False,
) -> ForecastResult:
    """Populate evidence/provenance fields on a ForecastResult.
    
    Args:
        result: The ForecastResult to annotate
        evidence_items: Nutrition source evidence
        historical_similarity_score: Match quality 0-1
        missing_info: Flags for missing context
        calibration: Calibration constants used (from ForecastStage.calibration)
        overwrite_drivers: If True, set top_drivers; if False, leave as-is
    """
    # Determine top drivers (only if not already set or overwrite requested)
    if overwrite_drivers or not result.top_drivers:
        drivers = []
        if result.meal_drivers.get("fast_carbs_g", 0) > 0:
            drivers.append(f"fast carbs ({result.meal_drivers['fast_carbs_g']}g)")
        if result.meal_drivers.get("slow_carbs_g", 0) > 0:
            drivers.append(f"slow carbs ({result.meal_drivers['slow_carbs_g']}g)")
        if result.meal_drivers.get("fat_triggers_delay"):
            drivers.append("fat/protein extended absorption")
        result.top_drivers = drivers
    
    result.historical_similarity_score = historical_similarity_score
    result.profile_assumptions = calibration or {}
    result.missing_information_flags = missing_info or []
    result.evidence_items = evidence_items or []
    
    return result
