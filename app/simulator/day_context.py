"""Daily context schedule generator for synthetic patients.

Generates a day's worth of event templates (meals, insulin, exercise, sleep)
based on the patient's anchor type and config. These templates are then
fed to the glucose engine to simulate CGM traces.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.simulator.schemas import AnchorType, EventCategory, PatientConfig


class DailySchedule:
    """A single day's scheduled events for a synthetic patient."""

    def __init__(
        self,
        date: datetime,
        meals: list[dict],
        insulin: list[dict],
        exercise: list[dict],
        sleep_start: Optional[datetime] = None,
        sleep_end: Optional[datetime] = None,
        illness: Optional[dict] = None,
        alcohol: Optional[dict] = None,
        stress: Optional[dict] = None,
    ):
        self.date = date
        self.meals = meals
        self.insulin = insulin
        self.exercise = exercise
        self.sleep_start = sleep_start
        self.sleep_end = sleep_end
        self.illness = illness
        self.alcohol = alcohol
        self.stress = stress

    def all_events(self) -> list[dict]:
        """Return all events as a flat list sorted by time."""
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
                "start_time": self.sleep_start,
                "end_time": self.sleep_end or (self.sleep_start + timedelta(hours=8)),
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
    """Generates daily context schedules for synthetic patients.

    Produces realistic meal times, insulin doses, exercise sessions,
    and sleep patterns that vary by anchor type.
    """

    # Meal timing templates (hour:minute offsets from midnight)
    MEAL_TIMES = {
        "breakfast": (7, 0),
        "lunch": (12, 30),
        "dinner": (18, 30),
        "snack_morning": (10, 0),
        "snack_afternoon": (15, 0),
        "snack_evening": (21, 0),
    }

    # Typical carb ranges by meal type (grams)
    CARB_RANGES = {
        "breakfast": (20, 50),
        "lunch": (40, 80),
        "dinner": (50, 100),
        "snack": (10, 30),
    }

    # Typical fat ranges by meal type (grams)
    FAT_RANGES = {
        "breakfast": (5, 15),
        "lunch": (10, 25),
        "dinner": (15, 40),
        "snack": (2, 10),
    }

    # Exercise timing and duration
    EXERCISE_TIMES = [(7, 0), (12, 0), (17, 0), (18, 0)]
    EXERCISE_DURATION_RANGE = (20, 60)

    def __init__(self, config: PatientConfig, rng: random.Random):
        self.config = config
        self.rng = rng

    def generate_day(self, base_date: datetime) -> DailySchedule:
        """Generate a full day of events.

        Args:
            base_date: Date for this day (time is set to midnight local).

        Returns:
            DailySchedule with meals, insulin, exercise, sleep.
        """
        day_start = base_date.replace(hour=0, minute=0, second=0, microsecond=0)

        meals = self._generate_meals(day_start)
        insulin = self._generate_insulin(day_start, meals)
        exercise = self._generate_exercise(day_start)
        sleep_start, sleep_end = self._generate_sleep(day_start)

        # Optional illness days (rare)
        illness = self._generate_optional_event(day_start, "illness", rate=0.01)

        # Optional alcohol events (evening, variable rate by anchor)
        alcohol_rate = 0.05 if self.config.anchor_type == AnchorType.BRITTLE else 0.02
        alcohol = self._generate_optional_event(day_start, "alcohol", rate=alcohol_rate)

        # Optional stress events
        stress_rate = 0.08 if self.config.anchor_type in (
            AnchorType.BRITTLE, AnchorType.HIGH_VARIABILITY
        ) else 0.03
        stress = self._generate_optional_event(day_start, "stress", rate=stress_rate)

        return DailySchedule(
            date=day_start,
            meals=meals,
            insulin=insulin,
            exercise=exercise,
            sleep_start=sleep_start,
            sleep_end=sleep_end,
            illness=illness,
            alcohol=alcohol,
            stress=stress,
        )

    # ── Meal generation ──

    def _generate_meals(self, day_start: datetime) -> list[dict]:
        """Generate meal events for the day."""
        meals = []
        base_hour = self.rng.randint(6, 9)
        base_min = self.rng.randint(0, 30)
        breakfast_time = day_start.replace(hour=base_hour, minute=base_min)

        meals.append(self._make_meal(
            "breakfast", breakfast_time,
            carbs=self.rng.randint(*self.CARB_RANGES["breakfast"]),
        ))

        # Lunch
        lunch_time = day_start.replace(hour=12, minute=self.rng.randint(0, 45))
        meals.append(self._make_meal(
            "lunch", lunch_time,
            carbs=self.rng.randint(*self.CARB_RANGES["lunch"]),
        ))

        # Dinner
        dinner_time = day_start.replace(hour=18, minute=self.rng.randint(0, 45))
        meals.append(self._make_meal(
            "dinner", dinner_time,
            carbs=self.rng.randint(*self.CARB_RANGES["dinner"]),
        ))

        # Occasional snacks
        if self.rng.random() < 0.4:
            snack_time = day_start.replace(hour=10, minute=self.rng.randint(0, 30))
            meals.append(self._make_meal(
                "snack_morning", snack_time,
                carbs=self.rng.randint(*self.CARB_RANGES["snack"]),
                fat=self.rng.randint(*self.FAT_RANGES["snack"]),
            ))
        if self.rng.random() < 0.3:
            snack_time = day_start.replace(hour=15, minute=self.rng.randint(0, 30))
            meals.append(self._make_meal(
                "snack_afternoon", snack_time,
                carbs=self.rng.randint(*self.CARB_RANGES["snack"]),
                fat=self.rng.randint(*self.FAT_RANGES["snack"]),
            ))

        meals.sort(key=lambda m: m["timestamp"])
        return meals

    def _make_meal(
        self,
        meal_type: str,
        timestamp: datetime,
        carbs: int,
        fat: Optional[int] = None,
    ) -> dict:
        """Create a meal event dict."""
        meal_names = {
            "breakfast": "Breakfast",
            "lunch": "Lunch",
            "dinner": "Dinner",
            "snack_morning": "Morning Snack",
            "snack_afternoon": "Afternoon Snack",
            "snack_evening": "Evening Snack",
        }
        if fat is None:
            fat = self.rng.randint(*self.FAT_RANGES.get(meal_type, (5, 15)))
        protein = self.rng.randint(int(carbs * 0.3), int(carbs * 0.6))
        return {
            "timestamp": timestamp,
            "type": meal_type,
            "description": meal_names.get(meal_type, "Meal"),
            "carbs_grams": float(carbs),
            "fat_grams": float(fat),
            "protein_grams": float(protein),
            "calories": int(carbs * 4 + protein * 4 + fat * 9),
            "is_high_fat": fat > 25,
        }

    # ── Insulin generation ──

    def _generate_insulin(self, day_start: datetime, meals: list[dict]) -> list[dict]:
        """Generate insulin doses aligned with meals and basal."""
        insulin_events = []

        # Basal — delivered as a continuous trickle: split into small hourly doses
        # Total daily basal ≈ (0.3 * total_meal_carbs) / carb_ratio
        total_carbs = sum(m["carbs_grams"] for m in meals)
        basal_total = round(0.3 * total_carbs / self.config.carb_ratio, 1)
        per_hour = round(basal_total / 24, 2)
        for hour in range(0, 24, 2):  # every 2 hours, small dose
            basal_time = day_start.replace(hour=hour, minute=self.rng.randint(0, 5))
            dose = round(per_hour * 2, 2)
            if dose > 0:
                insulin_events.append({
                    "timestamp": basal_time,
                    "type": "basal",
                    "units": dose,
                    "description": f"Basal {dose}u",
                })

        # Bolus for each meal
        for meal in meals:
            carb_ratio = self.config.carb_ratio
            correction = max(0, (self.config.basal_glucose_mean - 100) / self.config.insulin_sensitivity)
            bolus_units = round(meal["carbs_grams"] / carb_ratio + correction * 0.3, 1)
            bolus_units = max(0.5, bolus_units)

            # Timing: pre-bolus 0-15 min before meal
            bolus_time = meal["timestamp"] - timedelta(minutes=self.rng.randint(0, 15))

            insulin_events.append({
                "timestamp": bolus_time,
                "type": "bolus",
                "units": bolus_units,
                "description": f"Bolus {bolus_units}u for {meal['description']}",
                "meal_carbs": meal["carbs_grams"],
            })

        insulin_events.sort(key=lambda e: e["timestamp"])
        return insulin_events

    # ── Exercise generation ──

    def _generate_exercise(self, day_start: datetime) -> list[dict]:
        """Generate exercise events based on anchor type."""
        exercise_events = []
        exercise_frequency = 0.4  # base probability of exercising on any day

        # Some anchors exercise more
        if self.config.anchor_type == AnchorType.EXERCISE_REGIMEN:
            exercise_frequency = 0.85
        elif self.config.anchor_type == AnchorType.BRITTLE:
            exercise_frequency = 0.2
        elif self.config.anchor_type == AnchorType.NEWLY_DIAGNOSED:
            exercise_frequency = 0.25

        if self.rng.random() >= exercise_frequency:
            return exercise_events

        # Pick a random exercise time
        ex_hour, ex_min = self.rng.choice(self.EXERCISE_TIMES)
        ex_min += self.rng.randint(-15, 15)
        ex_time = day_start.replace(hour=ex_hour, minute=max(0, ex_min))
        duration = self.rng.randint(*self.EXERCISE_DURATION_RANGE)

        # Intensity proportional to duration
        if duration > 45:
            intensity = "high"
        elif duration > 30:
            intensity = "moderate"
        else:
            intensity = "low"

        types = ["cardio", "strength", "flexibility"]
        ex_type = self.rng.choice(types)

        exercise_events.append({
            "timestamp": ex_time,
            "duration_minutes": duration,
            "intensity": intensity,
            "type": ex_type,
            "description": f"{intensity.capitalize()} intensity {ex_type}",
        })

        return exercise_events

    # ── Sleep generation ──

    def _generate_sleep(self, day_start: datetime) -> tuple[datetime, datetime]:
        """Generate sleep start and end times."""
        sleep_hour = self.rng.randint(22, 23)
        sleep_min = self.rng.randint(0, 30)
        sleep_start = day_start.replace(hour=sleep_hour, minute=sleep_min)

        wake_hour = self.rng.randint(6, 8)
        wake_min = self.rng.randint(0, 30)
        sleep_end = (day_start + timedelta(days=1)).replace(hour=wake_hour, minute=wake_min)

        return sleep_start, sleep_end

    # ── Optional events ──

    def _generate_optional_event(
        self,
        day_start: datetime,
        event_type: str,
        rate: float,
    ) -> Optional[dict]:
        """Generate an optional event (illness, alcohol, stress) with given rate."""
        if self.rng.random() >= rate:
            return None

        if event_type == "illness":
            return {
                "timestamp": day_start.replace(hour=self.rng.randint(6, 12), minute=0),
                "type": "mild",
                "description": "Mild illness",
                "severity": 0.3,
            }
        elif event_type == "alcohol":
            return {
                "timestamp": day_start.replace(hour=self.rng.randint(19, 22), minute=0),
                "type": "alcohol",
                "description": "Alcoholic drink",
                "servings": self.rng.randint(1, 3),
            }
        elif event_type == "stress":
            return {
                "timestamp": day_start.replace(hour=self.rng.randint(9, 17), minute=0),
                "type": "work",
                "description": "Work stress",
                "severity": 0.5,
            }
        return None
