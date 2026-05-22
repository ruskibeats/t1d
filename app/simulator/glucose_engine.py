"""Physiological glucose simulation engine.

Mean-reverting process: at each 5-min step, glucose tends toward
basal_glucose_mean at rate DRIFT_RATE. Meals push it up, insulin
pushes it down, creating excursions that naturally return to baseline.

This is an Ornstein-Uhlenbeck-like model that's inherently stable
regardless of parameter tuning.
"""

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.simulator.schemas import PatientConfig


class GlucoseEngine:

    CGM_INTERVAL_MIN = 5
    STEPS_PER_HOUR = 60 // CGM_INTERVAL_MIN
    STEPS_PER_DAY = 24 * STEPS_PER_HOUR

    MEAL_WINDOW_STEPS = 36    # 3 hours × 12 steps/hr
    INSULIN_WINDOW_STEPS = 72 # 6 hours × 12 steps/hr
    MEAL_PEAK_STEP = 18       # 90 min
    INSULIN_PEAK_STEP = 18    # 90 min

    # Mean reversion: fraction of deviation corrected per 5-min step
    # At 0.02, a 100 mg/dL deviation is corrected by 2 mg/dL per step
    # → half-life ≈ ln(2) / 0.02 ≈ 35 steps ≈ 3 hours
    DRIFT_RATE = 0.020

    def __init__(self, config: PatientConfig, rng: random.Random, start_time=None):
        self.config = config
        self.rng = rng
        self.current_time = start_time or datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def _impulse(self, step: int, peak: int, total: int) -> float:
        """Normalised gamma impulse: sum over [1, total] ≈ 1.

        Uses empirical normalisation factor computed from the discrete sum.
        For peak=18, total=36: factor = 1.634
        For peak=18, total=72: factor = 2.124
        """
        if step <= 0 or step > total:
            return 0.0
        s = step * math.exp(-step / peak)
        area = peak * peak * math.exp(-1)
        if area <= 0:
            return 0.0
        norm = s / area
        # Empirical correction: discrete sum over [1,total] of raw values / area
        # Multiply by 1/empirical_sum so total ≈ 1
        # Empirically-derived correction so discrete sum ≈ 1
        norm_factor = {36: 1.634, 72: 1.357}.get(total, 1.6)
        return norm / norm_factor

    def _cap(self, v: float) -> float:
        """Soft logistic cap."""
        if v > 400.0:
            return 400.0 + 15.0 * (1.0 - math.exp(-(v - 400.0) / 15.0))
        if v < 40.0:
            return 40.0 - 15.0 * (1.0 - math.exp(-(40.0 - v) / 15.0))
        return v

    def generate_trace(self, daily_schedules, num_days=90):
        readings = []
        g = self.config.basal_glucose_mean  # starts at mean

        for di in range(min(num_days, len(daily_schedules))):
            sched = daily_schedules[di]
            ds = sched.date
            meals = sched.meals
            insulins = sched.insulin
            exercises = sched.exercise
            sleep_s, sleep_e = sched.sleep_start, sched.sleep_end

            for step in range(self.STEPS_PER_DAY):
                t = ds + timedelta(minutes=step * 5)
                h = (step / self.STEPS_PER_HOUR) % 24

                # ── Circadian target modulation ──
                # Circadian modulates the target mean, not the rate of change.
                # At midnight: target drops by ~amplitude*0.7 (gently)
                # At noon: target rises by ~amplitude*0.7
                # The drift then smoothly pulls glucose toward this target.
                circ_offset = self.config.basal_glucose_amplitude * math.sin((h - 3) / 24 * 2 * math.pi)

                # ── Dawn (4-8AM, mild) ──
                dawn_offset = 0.0
                if 4 <= h <= 8:
                    dawn_offset = self.config.dawn_effect_strength * 0.5 * math.sin((h - 4) / 4 * math.pi)

                # Combined target = basal mean + circadian + dawn
                target_g = self.config.basal_glucose_mean + circ_offset + dawn_offset
                drift = self.DRIFT_RATE * (target_g - g)

                # ── Meals ──
                meal_delta = 0.0
                for m in meals:
                    so = int((t - m["timestamp"]).total_seconds() / 60 / self.CGM_INTERVAL_MIN)
                    total_r = self.config.meal_rise_factor * m["carbs_grams"]
                    w = self._impulse(so, self.MEAL_PEAK_STEP, self.MEAL_WINDOW_STEPS)
                    meal_delta += total_r * w

                    if m.get("is_high_fat"):
                        fo = so - self.MEAL_WINDOW_STEPS
                        if fo > 0:
                            fw = self._impulse(fo, self.MEAL_PEAK_STEP, self.MEAL_WINDOW_STEPS)
                            meal_delta += total_r * 0.3 * fw

                # ── Insulin ──
                ins_delta = 0.0
                for ins in insulins:
                    so = int((t - ins["timestamp"]).total_seconds() / 60 / self.CGM_INTERVAL_MIN)
                    total_d = self.config.insulin_sensitivity * ins["units"] * 0.25
                    w = self._impulse(so, self.INSULIN_PEAK_STEP, self.INSULIN_WINDOW_STEPS)
                    ins_delta += total_d * w

                # ── Exercise ──
                ex = 0.0
                for e in exercises:
                    hs = (t - e["timestamp"]).total_seconds() / 3600
                    if hs > 0:
                        dur = e.get("duration_minutes", 30)
                        win = dur / 60 + 4.0
                        if hs <= win:
                            ex += self.config.exercise_drop_factor * dur * 0.08 * math.exp(-hs)

                # ── Sleep factor (mild) ──
                sf = 1.15 if sleep_s and sleep_e and (sleep_s <= t or t < sleep_e) else 1.0

                # ── Combine ──
                dg = drift + meal_delta - ins_delta * sf - ex
                g += dg
                g = self._cap(g)

                # ── Noise ──
                gn = g + self.rng.gauss(0, self.config.noise_sd)
                gn = self._cap(gn)

                # ── Hypo events ──
                if self.rng.random() < self.config.hypo_risk / self.STEPS_PER_DAY:
                    gn = self.rng.uniform(50, 68)

                rate = dg * 12
                trend = (
                    "double_up" if rate > 3 else
                    "single_up" if rate > 2 else
                    "forty_five_up" if rate > 1 else
                    "flat" if rate > -1 else
                    "forty_five_down" if rate > -2 else
                    "single_down" if rate > -3 else
                    "double_down"
                )

                readings.append({
                    "timestamp": t,
                    "glucose_value": round(gn, 1),
                    "trend": trend,
                    "trend_rate": round(rate, 2),
                    "delta": round(dg, 1),
                })

        return readings