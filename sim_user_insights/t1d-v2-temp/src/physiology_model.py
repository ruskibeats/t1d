#!/usr/bin/env python3
"""Open physiology-inspired glucose-insulin forecast model.

This is a transparent compartment model intended to replace ad-hoc impulse
forecasting in the companion pipeline. It is *not* a licensed UVA/Padova or
regulator-cleared simulator, but its state equations follow the same modelling
family used by validated T1D simulators: gut absorption compartments,
subcutaneous insulin absorption/action compartments, glucose mass balance,
endogenous return-to-basal, and renal clearance above threshold.

All state variables use user-facing units to keep the implementation auditable:
- glucose: mg/dL
- carbohydrate compartments: grams
- insulin compartments: units
- rates: per minute
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class PhysiologyParameters:
    """Patient/model parameters for the compartment forecast."""

    basal_mg_dl: float
    rise_per_g: float
    carb_ratio: float
    insulin_sensitivity: float
    balance_factor: float = 1.2
    exercise_heat_modifier: float = 1.0
    fat_delay_hours: float = 3.0

    # Gut absorption time constants. First-order absorption has mean=tau and
    # two-stage absorption peaks approximately at tau.
    fast_absorption_tau_min: float = 30.0
    slow_absorption_tau_min: float = 90.0
    delayed_absorption_tau_min: float = 150.0

    # Two-compartment subcutaneous insulin absorption/action model.
    insulin_action_tau_min: float = 75.0
    insulin_action_fraction: float = 0.25

    # Glucose dynamics.
    basal_reversion_per_min: float = 0.003  # 0.015 per 5-min step
    renal_threshold_mg_dl: float = 180.0
    renal_clearance_per_min: float = 0.001


@dataclass
class PhysiologyState:
    """Internal model state at a single instant."""

    glucose_mg_dl: float
    fast_gut_g: float = 0.0
    slow_gut_g: float = 0.0
    delayed_gut_g: float = 0.0
    insulin_sc1_u: float = 0.0
    insulin_sc2_u: float = 0.0
    delayed_seed_g: float = 0.0
    delayed_seed_released: bool = False


@dataclass(frozen=True)
class PhysiologyTracePoint:
    """Auditable trace point from the physiology forecast."""

    minute: int
    glucose_mg_dl: float
    meal_rate_mgdl_min: float
    insulin_rate_mgdl_min: float
    renal_rate_mgdl_min: float
    basal_rate_mgdl_min: float
    absorbed_carbs_g: float
    active_insulin_flux_u_min: float


@dataclass(frozen=True)
class PhysiologyTrace:
    """Full physiology simulation output."""

    points: list[PhysiologyTracePoint] = field(default_factory=list)

    def at_minute(self, minute: int) -> PhysiologyTracePoint:
        """Return the nearest point at or before minute."""
        if not self.points:
            raise ValueError("empty physiology trace")
        return min(self.points, key=lambda p: abs(p.minute - minute))

    @property
    def peak(self) -> PhysiologyTracePoint:
        if not self.points:
            raise ValueError("empty physiology trace")
        return max(self.points, key=lambda p: p.glucose_mg_dl)


def soft_glucose_cap(v: float) -> float:
    """Soft physiological CGM boundary, matching the simulator engine."""
    if v > 400.0:
        return 400.0 + 15.0 * (1.0 - math.exp(-(v - 400.0) / 15.0))
    if v < 40.0:
        return 40.0 - 15.0 * (1.0 - math.exp(-(40.0 - v) / 15.0))
    return v


class PhysiologyForecastModel:
    """Meal forecast using explicit glucose-insulin compartment equations.

    Difference equations, integrated by explicit Euler on a 5-minute grid:

    Gut absorption:
        dC_fast/dt    = -C_fast / tau_fast
        dC_slow/dt    = -C_slow / tau_slow
        dC_delayed/dt = -C_delayed / tau_delayed
        Ra_g_min      = C_fast/tau_fast*1.2 + C_slow/tau_slow + C_delayed/tau_delayed

    Insulin absorption/action:
        dI1/dt = -I1 / tau_I
        dI2/dt =  I1 / tau_I - I2 / tau_I
        insulin_flux_u_min = I2 / tau_I

    Glucose mass balance:
        dG/dt = meal_rate - insulin_rate - renal_rate + basal_reversion
        meal_rate    = rise_per_g * exercise_modifier * Ra_g_min
        insulin_rate = ISF * insulin_action_fraction * insulin_flux / balance_factor
        renal_rate   = k_renal * max(G - renal_threshold, 0)
        basal_rev    = k_basal * (G_basal - G)
    """

    def __init__(self, params: PhysiologyParameters):
        self.params = params

    def initialise_state(self, carbs_g: float, sugars_g: float, fat_g: float) -> PhysiologyState:
        sugars = max(0.0, min(float(sugars_g), float(carbs_g)))
        slow_carbs = max(float(carbs_g) - sugars, 0.0)

        # High-fat meals shift a fraction of slow carbs to a delayed compartment
        # instead of adding extra carbohydrate mass.
        delayed_fraction = 0.30 if fat_g >= 15.0 else 0.0
        immediate_slow = slow_carbs * (1.0 - delayed_fraction)
        delayed_seed = slow_carbs * delayed_fraction

        bolus_u = float(carbs_g) / self.params.carb_ratio if self.params.carb_ratio > 0 else 0.0
        return PhysiologyState(
            glucose_mg_dl=self.params.basal_mg_dl,
            fast_gut_g=sugars,
            slow_gut_g=immediate_slow,
            delayed_seed_g=delayed_seed,
            insulin_sc1_u=bolus_u,
        )

    def simulate(
        self,
        *,
        carbs_g: float,
        sugars_g: float = 0.0,
        fat_g: float = 0.0,
        horizon_minutes: int = 16 * 60,
        dt_minutes: int = 5,
    ) -> PhysiologyTrace:
        """Run a deterministic compartment forecast."""
        if dt_minutes <= 0:
            raise ValueError("dt_minutes must be positive")
        if horizon_minutes < 0:
            raise ValueError("horizon_minutes must be non-negative")

        state = self.initialise_state(carbs_g, sugars_g, fat_g)
        points: list[PhysiologyTracePoint] = []
        delayed_release_min = max(0, int(round(self.params.fat_delay_hours * 60)))

        for minute in range(0, horizon_minutes + 1, dt_minutes):
            if (
                state.delayed_seed_g > 0
                and not state.delayed_seed_released
                and minute >= delayed_release_min
            ):
                state.delayed_gut_g += state.delayed_seed_g
                state.delayed_seed_released = True

            fast_flux = state.fast_gut_g / self.params.fast_absorption_tau_min
            slow_flux = state.slow_gut_g / self.params.slow_absorption_tau_min
            delayed_flux = state.delayed_gut_g / self.params.delayed_absorption_tau_min
            absorbed_carbs_rate = fast_flux + slow_flux + delayed_flux

            meal_rate = (
                self.params.rise_per_g
                * self.params.exercise_heat_modifier
                * (1.2 * fast_flux + slow_flux + delayed_flux)
            )

            insulin_flux = state.insulin_sc2_u / self.params.insulin_action_tau_min
            insulin_rate = (
                self.params.insulin_sensitivity
                * self.params.insulin_action_fraction
                * insulin_flux
                / self.params.balance_factor
            )

            renal_rate = self.params.renal_clearance_per_min * max(
                state.glucose_mg_dl - self.params.renal_threshold_mg_dl, 0.0
            )
            basal_rate = self.params.basal_reversion_per_min * (
                self.params.basal_mg_dl - state.glucose_mg_dl
            )

            points.append(PhysiologyTracePoint(
                minute=minute,
                glucose_mg_dl=state.glucose_mg_dl,
                meal_rate_mgdl_min=meal_rate,
                insulin_rate_mgdl_min=insulin_rate,
                renal_rate_mgdl_min=renal_rate,
                basal_rate_mgdl_min=basal_rate,
                absorbed_carbs_g=absorbed_carbs_rate,
                active_insulin_flux_u_min=insulin_flux,
            ))

            # Euler step.
            state.fast_gut_g = max(0.0, state.fast_gut_g - dt_minutes * fast_flux)
            state.slow_gut_g = max(0.0, state.slow_gut_g - dt_minutes * slow_flux)
            state.delayed_gut_g = max(0.0, state.delayed_gut_g - dt_minutes * delayed_flux)

            d_i1 = -state.insulin_sc1_u / self.params.insulin_action_tau_min
            d_i2 = (
                state.insulin_sc1_u / self.params.insulin_action_tau_min
                - state.insulin_sc2_u / self.params.insulin_action_tau_min
            )
            state.insulin_sc1_u = max(0.0, state.insulin_sc1_u + dt_minutes * d_i1)
            state.insulin_sc2_u = max(0.0, state.insulin_sc2_u + dt_minutes * d_i2)

            d_glucose = meal_rate - insulin_rate - renal_rate + basal_rate
            state.glucose_mg_dl = soft_glucose_cap(state.glucose_mg_dl + dt_minutes * d_glucose)

        return PhysiologyTrace(points=points)
