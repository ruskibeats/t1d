#!/usr/bin/env python3
"""Forecast engine — functional pipeline (Design B).

Each kernel is an independently testable pure function.
Compose them in `forecast_glucose()`.
No I/O, no async, no DB. Only deterministic math.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

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
class ForecastResult:
    baseline_mg_dl: int
    peak_mg_dl: int
    peak_time_minutes: int
    forecast_points: list[ForecastPoint] = field(default_factory=list)
    nighttime: list[NighttimePoint] = field(default_factory=list)
    exercise_heat_modifier: float = 1.0
    meal_drivers: dict[str, Any] = field(default_factory=dict)


# ── Calibration maps ──

RISE_PER_CARB_MAP: dict[str, float] = {
    "well_controlled": 0.6, "high_fat_delayed": 0.75,
    "post_meal_spike": 0.9, "brittle": 0.85,
    "dawn_phenomenon": 0.5, "overnight_hypo": 0.55,
    "exercise_sensitive": 0.6, "exercise_regimen": 0.55,
    "insulin_sensitive": 0.5, "insulin_resistant": 0.85,
    "high_variability": 0.8, "newly_diagnosed": 0.9,
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

def gaussian_kernel(peak_min: float, width: float, t_min: float) -> float:
    """Unnormalised Gaussian kernel value at time t_min.

    peak_min — time of peak contribution (minutes)
    width — standard deviation (minutes)
    t_min — current time (minutes)
    """
    return math.exp(-((t_min - peak_min) ** 2) / (2 * width ** 2))


def project_fast_rise(
    sugars_g: float, rise_per_g: float
) -> tuple[float, int, int]:
    """Fast sugar rise: amplitude, peak minute, width.

    Returns (fast_rise_mg_dl, peak_min, width).
    """
    return (sugars_g * rise_per_g * 1.2, 25, 25)


def project_slow_rise(
    carbs_g: float, sugars_g: float, fat_g: float,
    rise_per_g: float, fat_delay_hours: float,
) -> tuple[float, int, int, bool, float]:
    """Slow starch rise with optional fat delay.

    Returns (slow_rise_mg_dl, peak_min, width, has_extended_tail, extended_tail_magnitude).
    """
    slow_carbs = max(carbs_g - sugars_g, 0)
    slow_rise = slow_carbs * rise_per_g
    base_peak_min = 90

    fat_shift = 0
    ext_tail = False
    if fat_g >= 15:
        fat_shift = int(fat_delay_hours * 60 * min(fat_g / 40, 1.5))
        ext_tail = True
    elif fat_g >= 8:
        fat_shift = int(fat_delay_hours * 30 * (fat_g / 15))

    slow_peak = base_peak_min + fat_shift
    return (slow_rise, slow_peak, 50, ext_tail, fat_delay_hours)


def project_insulin_effect(
    carbs_g: float, carb_ratio: float, insulin_sensitivity: float,
    balance_factor: float,
) -> tuple[float, int, int]:
    """Insulin glucose-lowering effect.

    Returns (insulin_drop_mg_dl, peak_min, width).
    """
    insulin_units = carbs_g / carb_ratio if carb_ratio else 0
    drop = insulin_units * insulin_sensitivity * 0.15 / balance_factor
    return (drop, 75, 60)


def compute_exercise_heat_modifier(exercise_drop_factor: float) -> float:
    """Compute modifier from profile's exercise drop factor."""
    if exercise_drop_factor <= 1:
        return 1.0
    return 1.0 - (1.0 - 1.0 / exercise_drop_factor) * 0.5


def compute_nighttime(
    trace: dict[int, float], basal: float,
    meal_hour: int, dt: int = 5,
) -> list[NighttimePoint]:
    """Compute nighttime forecast points from trace."""
    points = []
    for offset in [8, 10, 12, 14, 16]:
        t_min = offset * 60
        nearest = round(t_min / dt) * dt
        g = trace.get(nearest, basal)
        if g < 54:
            g = 54 + (g - 54) * 0.3
        hr = (meal_hour + offset) % 24
        note = "Falling" if g < basal - 20 else ("Rising" if g > basal + 20 else "Stable")
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

    # Project each kernel
    fast_amp, fast_peak, fast_width = project_fast_rise(totals.sugars_g, rise_per_g)
    slow_amp, slow_peak, slow_width, ext_tail, tail_hours = project_slow_rise(
        totals.carbs_g, totals.sugars_g, totals.fat_g, rise_per_g, fat_delay_hours,
    )
    insulin_amp, insulin_peak, insulin_width = project_insulin_effect(
        totals.carbs_g, carb_ratio, insulin_sensitivity, balance_factor,
    )
    heat_mod = compute_exercise_heat_modifier(exercise_drop_factor)

    # Scale by exercise/heat modifier
    fast_amp *= heat_mod
    slow_amp *= heat_mod

    # Simulate at dt resolution
    timepoints = [1, 2, 3, 4, 6, 8, 10]
    t_max = max(timepoints) * 60
    trace: dict[int, float] = {}
    ou_rate = 0.015
    basal = basal_mg_dl

    for t_min in range(0, t_max + 1, dt):
        g = basal + 5
        g += fast_amp * gaussian_kernel(fast_peak, fast_width, t_min)
        g += slow_amp * gaussian_kernel(slow_peak, slow_width, t_min)
        if ext_tail and t_min > slow_peak:
            g += slow_amp * 0.3 * math.exp(-(t_min - slow_peak) / (tail_hours * 120))
        g -= insulin_amp * gaussian_kernel(insulin_peak, insulin_width, t_min)
        g += (basal - g) * ou_rate * dt
        if g < 54:
            g = 54 + (g - 54) * 0.3
        trace[t_min] = g

    # Sample at requested timepoints
    points = [
        ForecastPoint(hour=hr, glucose_mg_dl=round(trace.get(hr * 60, basal)))
        for hr in timepoints
    ]

    # Find peak
    peak_t = max(trace, key=lambda t: trace[t])

    # Nighttime
    nighttime = compute_nighttime(trace, basal, hour, dt)

    return ForecastResult(
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
            "estimated_peak_rise_mg_dl": round(fast_amp + slow_amp),
            "insulin_units_estimated": round(totals.carbs_g / carb_ratio, 1) if carb_ratio else 0,
            "balance_factor": balance_factor,
        },
    )


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

    def forecast(self, totals: MealTotals, hour: int = 19) -> ForecastResult:
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