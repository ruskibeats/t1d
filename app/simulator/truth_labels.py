"""Plants hidden ground-truth labels for known patterns.

When the simulator generates events with known outcomes (e.g., a meal
guaranteed to spike, or overnight basal guaranteed to cause a low),
this module records the expected pattern characteristics in
sim_hidden_truths.

The pattern types align with PatternService detector outputs:
  - post_meal_spike
  - overnight_low
  - exercise_effect
  - delayed_high_fat
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.simulator.models import SimHiddenTruth
from app.simulator.schemas import PatientConfig

logger = logging.getLogger(__name__)


class TruthLabelPlacer:
    """Records planted ground-truth labels for detector evaluation.

    Each planted pattern gets a row in sim_hidden_truths with the
    expected characteristics. These are later compared against
    PatternService detector results.
    """

    # Minimum carb threshold to consider a meal a potential spike
    MIN_SPIKE_CARBS = 40
    # Minimum fat threshold for delayed effect
    MIN_DELAYED_FAT = 25
    # Minimum glucose drop to count as exercise effect
    MIN_EXERCISE_DROP = 30

    def __init__(self, db: AsyncSession, sim_run_id: int):
        self.db = db
        self.sim_run_id = sim_run_id

    async def plant_post_meal_spike_truths(
        self,
        sim_user_id: int,
        user_id: int,
        config: PatientConfig,
        meals: list[dict],
        cgm_readings: list[dict],
        sim_user_key: str,
    ) -> list[SimHiddenTruth]:
        """Plant truth labels for meal→glucose spike patterns.

        Records truths for meals with >= MIN_SPIKE_CARBS carbs that are
        expected to spike (based on meal_rise_factor and carb count).

        Args:
            sim_user_id: SimUser.id.
            user_id: User.id in tbl_users.
            config: Patient parameter config.
            meals: Meal events for the simulation period.
            cgm_readings: Full CGM trace.
            sim_user_key: SimUser.sim_user_key.

        Returns:
            List of created SimHiddenTruth instances.
        """
        planted: list[SimHiddenTruth] = []

        # Build lookup: timestamp → CGM reading
        cgm_by_time: dict[datetime, dict] = {}
        for r in cgm_readings:
            t = r["timestamp"].replace(tzinfo=None) if r["timestamp"].tzinfo else r["timestamp"]
            cgm_by_time[t] = r

        for meal in meals:
            carbs = meal.get("carbs_grams", 0)
            if carbs < self.MIN_SPIKE_CARBS:
                continue

            # Predict expected peak based on config
            expected_rise = config.meal_rise_factor * carbs
            meal_time = meal["timestamp"]
            meal_time_naive = meal_time.replace(tzinfo=None) if meal_time.tzinfo else meal_time

            # Find pre-meal glucose
            pre_meal_readings = [
                r for t, r in cgm_by_time.items()
                if meal_time_naive - timedelta(hours=1) <= t < meal_time_naive
            ]
            pre_meal_value = (
                sum(r["glucose_value"] for r in pre_meal_readings) / len(pre_meal_readings)
                if pre_meal_readings
                else config.basal_glucose_mean
            )

            expected_peak = pre_meal_value + expected_rise
            expected_time_to_peak = 60 + 30 * (carbs / 100)  # 60-90 min

            # Find actual peak in window
            window_end = meal_time_naive + timedelta(hours=3)
            post_meal_readings = [
                r for t, r in cgm_by_time.items()
                if meal_time_naive <= t <= window_end
            ]

            actual_peak = max((r["glucose_value"] for r in post_meal_readings), default=None)

            if actual_peak and actual_peak > 180:
                truth = SimHiddenTruth(
                    sim_run_id=self.sim_run_id,
                    sim_user_id=sim_user_id,
                    pattern_type="post_meal_spike",
                    subtype=meal.get("type", "meal"),
                    window_start=meal_time_naive,
                    window_end=window_end,
                    expected_peak_delta=round(expected_rise, 1),
                    expected_time_to_peak_min=round(expected_time_to_peak, 1),
                    expected_value_min=round(pre_meal_value, 1),
                    expected_value_max=round(expected_peak, 1),
                    truth_payload={
                        "sim_user_key": sim_user_key,
                        "carbs_grams": carbs,
                        "meal_type": meal.get("type"),
                        "description": meal.get("description"),
                        "is_high_fat": meal.get("is_high_fat", False),
                        "pre_meal_value": round(pre_meal_value, 1),
                        "expected_peak": round(expected_peak, 1),
                        "expected_rise": round(expected_rise, 1),
                        "meal_time": meal_time.isoformat(),
                    },
                )
                self.db.add(truth)
                planted.append(truth)

        await self.db.flush()
        for t in planted:
            await self.db.refresh(t)
        logger.info(f"Planted {len(planted)} post-meal spike truths for sim_user {sim_user_id}")
        return planted

    async def plant_overnight_low_truths(
        self,
        sim_user_id: int,
        user_id: int,
        config: PatientConfig,
        daily_schedules: list,
        cgm_readings: list[dict],
        sim_user_key: str,
    ) -> list[SimHiddenTruth]:
        """Plant truth labels for overnight hypoglycemia.

        Based on hypo_risk probability and overnight basal timing.
        Records expected low windows for each night with planted risk.

        Args:
            sim_user_id: SimUser.id.
            user_id: User.id in tbl_users.
            config: Patient parameter config.
            daily_schedules: List of DailySchedule objects.
            cgm_readings: Full CGM trace.
            sim_user_key: SimUser.sim_user_key.

        Returns:
            List of created SimHiddenTruth instances.
        """
        planted: list[SimHiddenTruth] = []
        cgm_by_time: dict[datetime, dict] = {}
        for r in cgm_readings:
            t = r["timestamp"].replace(tzinfo=None) if r["timestamp"].tzinfo else r["timestamp"]
            cgm_by_time[t] = r

        for schedule in daily_schedules:
            if not schedule.sleep_start or not schedule.sleep_end:
                continue

            sleep_start = schedule.sleep_start.replace(tzinfo=None) if schedule.sleep_start.tzinfo else schedule.sleep_start
            sleep_end = schedule.sleep_end.replace(tzinfo=None) if schedule.sleep_end.tzinfo else schedule.sleep_end

            # Check for lows during sleep
            night_readings = [
                r for t, r in cgm_by_time.items()
                if sleep_start <= t <= sleep_end
            ]

            if not night_readings:
                continue

            low_readings = [r for r in night_readings if r["glucose_value"] < 70]
            if low_readings:
                min_low = min(low_readings, key=lambda r: r["glucose_value"])
                lowest_value = min_low["glucose_value"]

                truth = SimHiddenTruth(
                    sim_run_id=self.sim_run_id,
                    sim_user_id=sim_user_id,
                    pattern_type="overnight_low",
                    subtype="hypoglycemia",
                    window_start=sleep_start,
                    window_end=sleep_end,
                    expected_value_min=round(lowest_value, 1),
                    expected_value_max=None,
                    expected_peak_delta=None,
                    expected_time_to_peak_min=None,
                    truth_payload={
                        "sim_user_key": sim_user_key,
                        "lowest_value": round(lowest_value, 1),
                        "total_readings": len(night_readings),
                        "low_readings": len(low_readings),
                        "low_percentage": round(len(low_readings) / len(night_readings) * 100, 1),
                        "sleep_start": sleep_start.isoformat(),
                        "sleep_end": sleep_end.isoformat(),
                    },
                )
                self.db.add(truth)
                planted.append(truth)

        await self.db.flush()
        for t in planted:
            await self.db.refresh(t)
        logger.info(f"Planted {len(planted)} overnight low truths for sim_user {sim_user_id}")
        return planted

    async def plant_exercise_effect_truths(
        self,
        sim_user_id: int,
        user_id: int,
        config: PatientConfig,
        daily_schedules: list,
        cgm_readings: list[dict],
        sim_user_key: str,
    ) -> list[SimHiddenTruth]:
        """Plant truth labels for exercise→glucose drop patterns.

        Args:
            sim_user_id: SimUser.id.
            user_id: User.id in tbl_users.
            config: Patient parameter config.
            daily_schedules: List of DailySchedule objects.
            cgm_readings: Full CGM trace.
            sim_user_key: SimUser.sim_user_key.

        Returns:
            List of created SimHiddenTruth instances.
        """
        planted: list[SimHiddenTruth] = []
        cgm_by_time: dict[datetime, dict] = {}
        for r in cgm_readings:
            t = r["timestamp"].replace(tzinfo=None) if r["timestamp"].tzinfo else r["timestamp"]
            cgm_by_time[t] = r

        for schedule in daily_schedules:
            for ex in schedule.exercise:
                ex_time = ex["timestamp"]
                ex_time_naive = ex_time.replace(tzinfo=None) if ex_time.tzinfo else ex_time

                # Get pre-exercise baseline
                pre_ex = [
                    r for t, r in cgm_by_time.items()
                    if ex_time_naive - timedelta(hours=1) <= t <= ex_time_naive
                ]
                if not pre_ex:
                    continue
                pre_value = sum(r["glucose_value"] for r in pre_ex) / len(pre_ex)

                # Get post-exercise minimum (within 4 hours)
                post_end = ex_time_naive + timedelta(hours=4)
                post_ex = [
                    r for t, r in cgm_by_time.items()
                    if ex_time_naive <= t <= post_end
                ]
                if not post_ex:
                    continue
                min_post = min(post_ex, key=lambda r: r["glucose_value"])
                drop = pre_value - min_post["glucose_value"]

                if drop >= self.MIN_EXERCISE_DROP:
                    truth = SimHiddenTruth(
                        sim_run_id=self.sim_run_id,
                        sim_user_id=sim_user_id,
                        pattern_type="exercise_effect",
                        subtype=ex.get("intensity", "moderate"),
                        window_start=ex_time_naive,
                        window_end=post_end,
                        expected_peak_delta=round(-drop, 1),
                        expected_value_min=round(min_post["glucose_value"], 1),
                        expected_value_max=round(pre_value, 1),
                        truth_payload={
                            "sim_user_key": sim_user_key,
                            "exercise_duration": ex.get("duration_minutes"),
                            "exercise_intensity": ex.get("intensity"),
                            "pre_exercise_value": round(pre_value, 1),
                            "min_post_exercise": round(min_post["glucose_value"], 1),
                            "drop": round(drop, 1),
                        },
                    )
                    self.db.add(truth)
                    planted.append(truth)

        await self.db.flush()
        for t in planted:
            await self.db.refresh(t)
        logger.info(f"Planted {len(planted)} exercise effect truths for sim_user {sim_user_id}")
        return planted

    async def plant_delayed_high_fat_truths(
        self,
        sim_user_id: int,
        user_id: int,
        config: PatientConfig,
        daily_schedules: list,
        cgm_readings: list[dict],
        sim_user_key: str,
    ) -> list[SimHiddenTruth]:
        """Plant truth labels for delayed high-fat meal spikes.

        Args:
            sim_user_id: SimUser.id.
            user_id: User.id in tbl_users.
            config: Patient parameter config.
            daily_schedules: List of DailySchedule objects.
            cgm_readings: Full CGM trace.
            sim_user_key: SimUser.sim_user_key.

        Returns:
            List of created SimHiddenTruth instances.
        """
        planted: list[SimHiddenTruth] = []
        cgm_by_time: dict[datetime, dict] = {}
        for r in cgm_readings:
            t = r["timestamp"].replace(tzinfo=None) if r["timestamp"].tzinfo else r["timestamp"]
            cgm_by_time[t] = r

        for schedule in daily_schedules:
            for meal in schedule.meals:
                if not meal.get("is_high_fat", False):
                    continue

                meal_time = meal["timestamp"]
                meal_time_naive = meal_time.replace(tzinfo=None) if meal_time.tzinfo else meal_time
                delay_hours = config.fat_delay_hours
                delay_start = meal_time_naive + timedelta(hours=delay_hours)
                delay_end = delay_start + timedelta(hours=3)

                # Get glucose in delayed window
                delayed_readings = [
                    r for t, r in cgm_by_time.items()
                    if delay_start <= t <= delay_end
                ]
                if not delayed_readings:
                    continue

                peak_delayed = max(delayed_readings, key=lambda r: r["glucose_value"])
                if peak_delayed["glucose_value"] > 180:
                    truth = SimHiddenTruth(
                        sim_run_id=self.sim_run_id,
                        sim_user_id=sim_user_id,
                        pattern_type="delayed_high_fat",
                        subtype="delayed_spike",
                        window_start=delay_start,
                        window_end=delay_end,
                        expected_value_min=None,
                        expected_value_max=round(peak_delayed["glucose_value"], 1),
                        expected_time_to_peak_min=round(delay_hours * 60, 1),
                        truth_payload={
                            "sim_user_key": sim_user_key,
                            "meal_time": meal_time.isoformat(),
                            "carbs_grams": meal.get("carbs_grams"),
                            "fat_grams": meal.get("fat_grams"),
                            "delay_hours": delay_hours,
                            "peak_value": round(peak_delayed["glucose_value"], 1),
                            "peak_time": peak_delayed["timestamp"].isoformat(),
                        },
                    )
                    self.db.add(truth)
                    planted.append(truth)

        await self.db.flush()
        for t in planted:
            await self.db.refresh(t)
        logger.info(f"Planted {len(planted)} delayed high-fat truths for sim_user {sim_user_id}")
        return planted

    async def plant_all_truths(
        self,
        sim_user_id: int,
        user_id: int,
        config: PatientConfig,
        daily_schedules: list,
        cgm_readings: list[dict],
        sim_user_key: str,
    ) -> list[SimHiddenTruth]:
        """Plant all truth label types for a single patient.

        Args:
            sim_user_id: SimUser.id.
            user_id: User.id in tbl_users.
            config: Patient parameter config.
            daily_schedules: List of DailySchedule objects.
            cgm_readings: Full CGM trace.
            sim_user_key: SimUser.sim_user_key.

        Returns:
            All planted SimHiddenTruth instances.
        """
        all_truths: list[SimHiddenTruth] = []

        # Collect all meals across all days
        all_meals = []
        for sched in daily_schedules:
            all_meals.extend(sched.meals)

        spike_truths = await self.plant_post_meal_spike_truths(
            sim_user_id, user_id, config, all_meals, cgm_readings, sim_user_key,
        )
        all_truths.extend(spike_truths)

        overnight_truths = await self.plant_overnight_low_truths(
            sim_user_id, user_id, config, daily_schedules, cgm_readings, sim_user_key,
        )
        all_truths.extend(overnight_truths)

        exercise_truths = await self.plant_exercise_effect_truths(
            sim_user_id, user_id, config, daily_schedules, cgm_readings, sim_user_key,
        )
        all_truths.extend(exercise_truths)

        fat_truths = await self.plant_delayed_high_fat_truths(
            sim_user_id, user_id, config, daily_schedules, cgm_readings, sim_user_key,
        )
        all_truths.extend(fat_truths)

        logger.info(
            f"Total planted truths for sim_user {sim_user_id}: {len(all_truths)} "
            f"({len(spike_truths)} spikes, {len(overnight_truths)} overnight, "
            f"{len(exercise_truths)} exercise, {len(fat_truths)} delayed fat)"
        )
        return all_truths
