"""Physiological glucose simulation engine.

Generates realistic CGM traces from daily event schedules using a
compartmental model:
  - Circadian baseline (sinusoidal rhythm with dawn phenomenon)
  - Meal response (carb absorption → glucose rise)
  - Insulin effect (glucose clearance proportional to insulin on board)
  - Exercise effect (temporary glucose uptake increase)
  - Stochastic noise

The model is simplified but captures the key dynamics needed to stress-test
pattern detectors: post-meal spikes, overnight lows, exercise drops, and
delayed high-fat effects.
"""

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.simulator.schemas import PatientConfig


class GlucoseEngine:
    """Simulates continuous glucose monitor readings.

    Produces 5-minute interval CGM traces over one or more days,
    driven by meal, insulin, exercise, and sleep events.

    The model uses discrete 5-min timesteps with:
    - G(t+1) = G(t) + dG_basal + dG_meal + dG_insulin + dG_exercise + noise
    """

    # CGM sampling interval in minutes
    CGM_INTERVAL_MIN = 5
    SAMPLES_PER_HOUR = 60 // CGM_INTERVAL_MIN
    SAMPLES_PER_DAY = 24 * SAMPLES_PER_HOUR

    # Physiological constants
    MEAL_ABSORPTION_RATE = 0.015  # per 5-min step, carb → glucose
    INSULIN_ACTION_RATE = 0.025   # per 5-min step
    EXERCISE_RECOVERY_RATE = 0.01  # per 5-min step

    def __init__(
        self,
        config: PatientConfig,
        rng: random.Random,
        start_time: Optional[datetime] = None,
    ):
        """Initialize the engine for a simulation period.

        Args:
            config: Patient parameter config.
            rng: Seeded RNG for reproducibility.
            start_time: Start time (defaults to engine creation time).
        """
        self.config = config
        self.rng = rng
        self.current_time = start_time or datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def generate_trace(
        self,
        daily_schedules: list,
        num_days: int = 90,
    ) -> list[dict]:
        """Generate a CGM trace over multiple days.

        Args:
            daily_schedules: List of DailySchedule objects.
            num_days: Number of days to simulate.

        Returns:
            List of {timestamp, glucose_value, trend} dicts at 5-min intervals.
        """
        readings: list[dict] = []
        glucose = self.config.basal_glucose_mean

        # Track insulin on board (IOB)
        iob = 0.0
        # Track exercise recovery
        exercise_effect = 0.0
        # Track carb absorption
        carbs_absorbing: list[dict] = []
        # Track high-fat delayed effect
        fat_effect = 0.0

        for day_idx in range(min(num_days, len(daily_schedules))):
            schedule = daily_schedules[day_idx]
            day_start = schedule.date

            # Pre-process day events into active buffers
            meals_today = schedule.meals
            insulin_today = schedule.insulin
            exercise_today = schedule.exercise
            sleep_start = schedule.sleep_start
            sleep_end = schedule.sleep_end
            illness = schedule.illness
            alcohol = schedule.alcohol
            stress = schedule.stress

            # Generate 5-min readings for this day
            for step in range(self.SAMPLES_PER_DAY):
                current_time = day_start + timedelta(minutes=step * 5)

                # ── Circadian baseline ──
                hour_fraction = (step / self.SAMPLES_PER_HOUR) % 24
                circadian = self._circadian_component(hour_fraction)

                basal = self.config.basal_glucose_mean

                # ── Dawn phenomenon (4 AM - 8 AM rise) ──
                dawn = 0.0
                if 4 <= hour_fraction <= 8:
                    dawn_progress = (hour_fraction - 4) / 4
                    dawn = self.config.dawn_effect_strength * math.sin(
                        dawn_progress * math.pi
                    )

                # ── Illness effect (mild sustained rise) ──
                illness_effect = 0.0
                if illness and current_time >= illness["timestamp"]:
                    illness_effect = 20.0 * illness.get("severity", 0.3) * math.exp(
                        -((current_time - illness["timestamp"]).total_seconds() / 3600) / 24
                    )

                # ── Alcohol effect (initial rise then drop) ──
                alcohol_effect = 0.0
                if alcohol and current_time >= alcohol["timestamp"]:
                    hours_since = (current_time - alcohol["timestamp"]).total_seconds() / 3600
                    if hours_since <= 2:
                        alcohol_effect = 10 * alcohol.get("servings", 1) * (hours_since / 2)
                    else:
                        alcohol_effect = -15 * alcohol.get("servings", 1) * min(1, (hours_since - 2) / 6)

                # ── Stress effect (moderate rise during work hours) ──
                stress_effect = 0.0
                if stress and current_time >= stress["timestamp"]:
                    hours_since = (current_time - stress["timestamp"]).total_seconds() / 3600
                    if hours_since <= 4:
                        stress_effect = 15.0 * stress.get("severity", 0.5) * (1 - hours_since / 4)

                # ── Carb absorption ──
                meal_input = 0.0
                for meal in meals_today:
                    meal_time = meal["timestamp"]
                    if meal_time <= current_time:
                        hours_since_meal = (current_time - meal_time).total_seconds() / 3600
                        if hours_since_meal <= 3:
                            # Absorption curve: rise over 30-90 min, then decay
                            absorption = self.config.meal_rise_factor * meal["carbs_grams"]
                            phase = hours_since_meal / 1.5  # peak at ~1.5h
                            meal_input += absorption * phase * math.exp(-phase)

                            # Delayed high-fat effect
                            if meal.get("is_high_fat", False):
                                fat_delay = self.config.fat_delay_hours
                                if hours_since_meal >= fat_delay and hours_since_meal <= fat_delay + 3:
                                    fat_phase = (hours_since_meal - fat_delay) / 1.5
                                    fat_effect += self.config.meal_rise_factor * meal["carbs_grams"] * 0.3 * fat_phase * math.exp(-fat_phase)

                # ── Insulin effect ──
                insulin_input = 0.0
                for ins in insulin_today:
                    ins_time = ins["timestamp"]
                    if ins_time <= current_time:
                        hours_since_ins = (current_time - ins_time).total_seconds() / 3600
                        if hours_since_ins <= 6:
                            # Insulin action: peak at 1-2h, lasts 4-6h
                            iob_phase = hours_since_ins / 1.5
                            iob_decay = math.exp(-iob_phase)
                            insulin_input += self.config.insulin_sensitivity * ins["units"] * iob_phase * iob_decay * 0.15

                # ── Exercise effect ──
                ex_effect = 0.0
                for ex in exercise_today:
                    ex_time = ex["timestamp"]
                    duration = ex.get("duration_minutes", 30)
                    if ex_time <= current_time:
                        hours_since_ex = (current_time - ex_time).total_seconds() / 3600
                        if hours_since_ex <= duration / 60 + 4:
                            ex_effect += self.config.exercise_drop_factor * duration * math.exp(-hours_since_ex)

                # ── Time-dependent safety ──
                # During sleep (after sleep_start, before sleep_end), insulin sensitivity increases
                sleep_factor = 1.0
                if sleep_start and sleep_end:
                    if sleep_start <= current_time or current_time < sleep_end:
                        sleep_factor = 1.3  # 30% more insulin sensitive during sleep

                # ── Glucose update ──
                delta = (
                    circadian                     # circadian variation
                    + dawn                         # dawn phenomenon rise
                    + meal_input                   # carb absorption
                    + illness_effect               # illness rise
                    + alcohol_effect               # alcohol effect
                    + stress_effect                # stress rise
                    + fat_effect                   # delayed fat rise
                    - insulin_input * sleep_factor  # insulin-driven drop
                    - ex_effect                    # exercise-driven drop
                )

                glucose += delta

                # Clamp to physiological range
                glucose = max(40, min(400, glucose))

                # ── Trend calculation ──
                trend, trend_rate = self._calculate_trend(
                    glucose, delta, current_time
                )

                # ── Add stochastic noise ──
                noise = self.rng.gauss(0, self.config.noise_sd)
                glucose_noisy = glucose + noise
                glucose_noisy = max(40, min(400, glucose_noisy))

                # ── Planted hypo events ──
                # Some anchors have higher hypo rates
                if self.rng.random() < self.config.hypo_risk / self.SAMPLES_PER_DAY:
                    glucose_noisy = self.rng.uniform(50, 68)

                readings.append({
                    "timestamp": current_time,
                    "glucose_value": round(glucose_noisy, 1),
                    "trend": trend,
                    "trend_rate": trend_rate,
                    "delta": round(delta, 1),
                })

        return readings

    def _circadian_component(self, hour: float) -> float:
        """Circadian glucose variation: ~sinusoidal with 24h period.

        Trough around 3-4 AM, peak around late afternoon.
        """
        # Shift so trough is ~3 AM, peak ~3 PM
        phase = (hour - 3) / 24 * 2 * math.pi
        amplitude = self.config.basal_glucose_amplitude
        return amplitude * math.sin(phase)

    def _calculate_trend(
        self,
        glucose: float,
        delta: float,
        current_time: datetime,
    ) -> tuple[str, float]:
        """Calculate Dexcom-style trend direction and rate.

        Args:
            glucose: Current glucose value.
            delta: Change since last reading.
            current_time: Current timestamp.

        Returns:
            (trend_string, trend_rate)
        """
        rate = round(delta * (60 / self.CGM_INTERVAL_MIN), 2)

        if rate > 3:
            trend = "double_up"
        elif rate > 2:
            trend = "single_up"
        elif rate > 1:
            trend = "forty_five_up"
        elif rate > -1:
            trend = "flat"
        elif rate > -2:
            trend = "forty_five_down"
        elif rate > -3:
            trend = "single_down"
        else:
            trend = "double_down"

        return trend, rate
