"""Daily context schedule generator for synthetic patients.

Generates a day's worth of event templates (meals, insulin, exercise, sleep)
based on the patient's anchor type. These templates drive the glucose engine
to produce clinically plausible CGM traces per the calibration spec.

Key calibration targets (well_controlled):
  - Range: 80-180 most of day, overnight 95-125, waking 100-130
  - Meal peaks: 145-175, rises of 40-70 above pre-meal baseline
  - Recovery: return toward baseline within 2-4 hours
  - Almost never above 220
  - TIR >70%, <4% below 70, <1% below 54, <25% above 180

Approach:
  - No basal insulin (engine's mean-reverting drift handles overnight stability)
  - Meal boluses deliberately ~10% under-bolus for modest post-meal rise
  - Insulin action window matches rapid-acting insulin (~4h)
  - Tier 1 realism: small carb miscounts, slightly delayed bolus sometimes
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.simulator.schemas import AnchorType, EventCategory, PatientConfig


class DailySchedule:
    """A single day's scheduled events for a synthetic patient."""

    def __init__(self, date, meals, insulin, exercise, sleep_start=None, sleep_end=None,
                 illness=None, alcohol=None, stress=None):
        self.date = date
        self.meals = meals
        self.insulin = insulin
        self.exercise = exercise
        self.sleep_start = sleep_start
        self.sleep_end = sleep_end
        self.illness = illness
        self.alcohol = alcohol
        self.stress = stress

    def all_events(self):
        """Return all events as a flat list sorted by time."""
        from app.simulator.schemas import EventCategory
        events = []
        for meal in self.meals:
            events.append({"category": EventCategory.MEAL, **meal})
        for ins in self.insulin:
            events.append({"category": EventCategory.INSULIN, **ins})
        for ex in self.exercise:
            events.append({"category": EventCategory.EXERCISE, **ex})
        if self.sleep_start:
            events.append({
                "category": EventCategory.SLEEP,
                "start_time": self.sleep_start, "end_time": self.sleep_end,
                "type": "night",
            })
        if self.illness:
            events.append({"category": EventCategory.ILLNESS, **self.illness})
        if self.alcohol:
            events.append({"category": EventCategory.ALCOHOL, **self.alcohol})
        if self.stress:
            events.append({"category": EventCategory.STRESS, **self.stress})
        events.sort(key=lambda e: e.get("start_time") or e.get("timestamp") or datetime.min)
        return events


class DayContextGenerator:
    """Generates daily context schedules for synthetic patients."""

    # Carb ranges by anchor and meal type (min, max grams)
    # Well-controlled keeps things moderate
    CARBS = {
        AnchorType.WELL_CONTROLLED: {
            "breakfast": (20, 35), "lunch": (30, 50), "dinner": (35, 55), "snack": (8, 15),
        },
        AnchorType.POST_MEAL_SPIKE: {
            "breakfast": (20, 35), "lunch": (30, 45), "dinner": (35, 55), "snack": (8, 15),
        },
        AnchorType.OVERNIGHT_HYPO: {
            "breakfast": (25, 45), "lunch": (35, 60), "dinner": (45, 70), "snack": (10, 20),
        },
        AnchorType.BRITTLE: {
            "breakfast": (20, 45), "lunch": (25, 55), "dinner": (30, 70), "snack": (8, 20),
        },
    }
    # Default for unlisted anchors
    DEFAULT_CARBS = {"breakfast": (25, 50), "lunch": (35, 70), "dinner": (45, 80), "snack": (10, 25)}

    def __init__(self, config: PatientConfig, rng: random.Random):
        self.config = config
        self.rng = rng

    def _meal_ranges(self, meal_type):
        """Get carb range for this anchor and meal type."""
        anchor_carbs = self.CARBS.get(self.config.anchor_type, self.DEFAULT_CARBS)
        return anchor_carbs.get(meal_type, self.DEFAULT_CARBS.get(meal_type, (20, 50)))

    def generate_day(self, base_date):
        """Generate a full day of events."""
        ds = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
        meals = self._generate_meals(ds)
        insulin = self._generate_insulin(ds, meals)
        exercise = self._generate_exercise(ds)
        sleep_start, sleep_end = self._generate_sleep(ds)
        illness = self._optional_event(ds, "illness", 0.01)
        alcohol_rate = 0.05 if self.config.anchor_type == AnchorType.BRITTLE else 0.02
        alcohol = self._optional_event(ds, "alcohol", alcohol_rate)
        stress_rate = 0.08 if self.config.anchor_type in (AnchorType.BRITTLE, AnchorType.HIGH_VARIABILITY) else 0.03
        stress = self._optional_event(ds, "stress", stress_rate)
        return DailySchedule(ds, meals, insulin, exercise, sleep_start, sleep_end, illness, alcohol, stress)

    def _generate_meals(self, ds):
        """Generate meals sized for the anchor type."""
        meals = []
        anchor = self.config.anchor_type

        # Breakfast: ~7-8AM
        bt = ds.replace(hour=self.rng.randint(6, 8), minute=self.rng.randint(0, 30))
        lo, hi = self._meal_ranges("breakfast")
        meals.append(self._make_meal("breakfast", bt, self.rng.randint(lo, hi)))

        # Snack frequency depends on anchor
        snack_rate = 0.1 if anchor == AnchorType.WELL_CONTROLLED else (0.35 if anchor == AnchorType.BRITTLE else 0.2)

        # Morning snack: occasional
        if self.rng.random() < snack_rate:
            lo, hi = self._meal_ranges("snack")
            st = ds.replace(hour=10, minute=self.rng.randint(0, 30))
            meals.append(self._make_meal("snack_morning", st, self.rng.randint(lo, hi)))

        # Lunch: ~12-1PM
        lt = ds.replace(hour=12, minute=self.rng.randint(0, 45))
        lo, hi = self._meal_ranges("lunch")
        meals.append(self._make_meal("lunch", lt, self.rng.randint(lo, hi)))

        # Afternoon snack: rare for well_controlled
        if self.rng.random() < snack_rate:
            lo, hi = self._meal_ranges("snack")
            st = ds.replace(hour=15, minute=self.rng.randint(0, 30))
            meals.append(self._make_meal("snack_afternoon", st, self.rng.randint(lo, hi)))

        # Dinner: ~6-7:30PM
        dt = ds.replace(hour=self.rng.randint(18, 19), minute=self.rng.randint(0, 30))
        lo, hi = self._meal_ranges("dinner")
        high_fat_chance = 0.3 if anchor == AnchorType.HIGH_FAT_DELAYED else 0.1
        meals.append(self._make_meal("dinner", dt, self.rng.randint(lo, hi), high_fat_chance=high_fat_chance))

        meals.sort(key=lambda m: m["timestamp"])
        return meals

    def _make_meal(self, meal_type, timestamp, carbs, high_fat_chance=0.0):
        """Create a meal event with appropriate macros."""
        names = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner",
                 "snack_morning": "Morning Snack", "snack_afternoon": "Afternoon Snack"}
        fat = self.rng.randint(5, max(5, min(25, int(carbs * 0.4))))
        protein = self.rng.randint(int(carbs * 0.3), int(carbs * 0.6))
        is_high_fat = fat > 20 or (high_fat_chance > 0 and self.rng.random() < high_fat_chance and fat > 15)
        return {
            "timestamp": timestamp,
            "type": meal_type,
            "description": names.get(meal_type, "Meal"),
            "carbs_grams": float(carbs),
            "fat_grams": float(fat),
            "protein_grams": float(protein),
            "calories": int(carbs * 4 + protein * 4 + fat * 9),
            "is_high_fat": is_high_fat,
        }

    def _generate_insulin(self, ds, meals):
        """Generate meal boluses plus small pre-meal basal to prevent cumulative drift.

        Boluses are ~15% smaller than 'perfect' (Tier 1 realism) to produce
        modest post-meal rises of 40-70 mg/dL.
        Pre-meal basal (0.3-0.5u) prevents baseline from creeping up across the day.

        Anchor-specific tweaks:
        - post_meal_spike: one meal per day gets a delayed bolus or under-bolus (~25% short)
        - overnight_hypo: possibly over-bolus dinner slightly
        """
        events = []
        carbs_r = self.config.carb_ratio
        sens = self.config.insulin_sensitivity

        for meal in meals:
            # Add small pre-meal basal (0.3-0.5u) 30 min before meal to prevent drift
            basal_time = meal["timestamp"] - timedelta(minutes=30)
            basal_units = 0.3 + self.rng.random() * 0.2  # 0.3-0.5u
            events.append({
                "timestamp": basal_time,
                "type": "basal",
                "units": round(basal_units, 1),
                "description": f"Pre-meal basal {basal_units:.1f}u",
                "meal_carbs": 0,  # basal not tied to carbs
            })

            perfect_bolus = meal["carbs_grams"] / carbs_r

            # Anchor-specific imperfection
            if self.config.anchor_type == AnchorType.OVERNIGHT_HYPO and meal["type"] == "dinner":
                # Slightly over-bolus dinner to increase overnight hypo risk
                bolus = round(perfect_bolus * 1.1, 1)
            elif self.config.anchor_type == AnchorType.BRITTLE:
                # Random bolus error ±30%
                bolus = round(perfect_bolus * (0.7 + self.rng.random() * 0.6), 1)
            else:
                # Tier 1 realism: one-meal-at-a-time under-bolus
                # Most meals are well-bolused (good recovery). One meal/day gets under-bolused.
                key = (self.config.anchor_type, meal["type"])
                
                # Define which meal gets the deliberate under-bolus
                if self.config.anchor_type == AnchorType.POST_MEAL_SPIKE and meal["type"] == "lunch":
                    under_bolus_factor = 0.75 + self.rng.random() * 0.08
                elif self.config.anchor_type == AnchorType.OVERNIGHT_HYPO and meal["type"] == "dinner":
                    under_bolus_factor = 0.75 + self.rng.random() * 0.10
                elif self.config.anchor_type == AnchorType.BRITTLE:
                    under_bolus_factor = 0.65 + self.rng.random() * 0.20
                else:
                    # Well-bolused: returns to baseline between meals
                    under_bolus_factor = 0.90 + self.rng.random() * 0.06
                bolus = round(perfect_bolus * under_bolus_factor, 1)

            bolus = max(0.3, bolus)

            # Timing: mostly pre-bolus (0-10 min), sometimes post-bolus (delayed)
            if self.config.anchor_type == AnchorType.POST_MEAL_SPIKE and meal["type"] == "lunch":
                # Delayed bolus: 10-20 min AFTER meal
                bolus_time = meal["timestamp"] + timedelta(minutes=self.rng.randint(10, 20))
            elif self.rng.random() < 0.1:
                # Occasional late bolus for realism
                bolus_time = meal["timestamp"] + timedelta(minutes=self.rng.randint(5, 15))
            else:
                bolus_time = meal["timestamp"] - timedelta(minutes=self.rng.randint(0, 10))

            events.append({
                "timestamp": bolus_time,
                "type": "bolus",
                "units": bolus,
                "description": f"Bolus {bolus}u for {meal['description']}",
                "meal_carbs": meal["carbs_grams"],
            })

        events.sort(key=lambda e: e["timestamp"])
        return events

    def _generate_exercise(self, ds):
        """Generate exercise events by anchor type."""
        freq = {"well_controlled": 0.4, "post_meal_spike": 0.3, "overnight_hypo": 0.3,
                "brittle": 0.15, "exercise_regimen": 0.85}
        base = self.config.anchor_type.value
        if self.rng.random() >= freq.get(base, 0.3):
            return []

        hour, minute = self.rng.choice([(7, 0), (12, 0), (17, 0), (18, 0)])
        ex_time = ds.replace(hour=hour, minute=max(0, minute + self.rng.randint(-10, 10)))
        duration = self.rng.randint(20, 50)

        intensity = "high" if duration > 40 else ("moderate" if duration > 28 else "low")
        types = ["cardio", "strength", "mixed"]
        return [{
            "timestamp": ex_time,
            "duration_minutes": duration,
            "intensity": intensity,
            "type": self.rng.choice(types),
            "description": f"{intensity} {self.rng.choice(types)}",
        }]

    def _generate_sleep(self, ds):
        """Sleep ~11PM to ~7AM with some jitter."""
        sh = self.rng.randint(22, 23)  # 10-11 PM
        sleep_start = ds.replace(hour=sh, minute=self.rng.randint(0, 30))
        wh = self.rng.randint(6, 8)  # 6-8 AM
        sleep_end = (ds + timedelta(days=1)).replace(hour=wh, minute=self.rng.randint(0, 30))
        return sleep_start, sleep_end

    def _optional_event(self, ds, etype, rate):
        if self.rng.random() >= rate:
            return None
        if etype == "illness":
            return {"timestamp": ds.replace(hour=8, minute=0), "type": "mild", "severity": 0.3}
        if etype == "alcohol":
            return {"timestamp": ds.replace(hour=20, minute=0), "type": "alcohol", "servings": self.rng.randint(1, 3)}
        if etype == "stress":
            return {"timestamp": ds.replace(hour=10, minute=0), "type": "work", "severity": 0.5}
        return None