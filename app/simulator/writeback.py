"""Writes synthetic patient data into existing database tables.

Preserves compatibility with the existing PatternService by writing
into the same tables real data uses:
  - health_metrics (unified metric store)
  - health_metric_edges (graph edges — optional)
  - tbl_glucose_readings (legacy)
  - tbl_context_events (legacy events)
  - tbl_users (sim user registration)

All simulator-origin data is tagged with source="simulator" and the
sim run / sim user key in meta.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContextEvent, GlucoseReading, User
from app.metrics.models import HealthMetric
from app.metrics.models import HealthMetric
from app.metrics.schemas import BatchHealthMetricCreate, HealthMetricCreate
from app.metrics.service import HealthMetricService
from app.metrics.types import MetricType
from app.simulator.schemas import PatientConfig

logger = logging.getLogger(__name__)


class SimulatorWriteback:
    """Writes synthetic data into production tables.

    All writes use source="simulator" and embed sim_run_id + sim_user_key
    in meta for traceability.
    """

    def __init__(self, db: AsyncSession, sim_run_id: int, sim_user_key: str):
        self.db = db
        self.sim_run_id = sim_run_id
        self.sim_user_key = sim_user_key
        self.metric_service = HealthMetricService(db)

    # ── Sim User Registration ──

    async def register_sim_user(
        self,
        config: PatientConfig,
        profile_json: dict,
    ) -> User:
        """Create a dummy User record for the synthetic patient.

        Args:
            config: Patient parameter config.
            profile_json: Human-readable profile metadata.

        Returns:
            Created User instance.
        """
        user = User(
            email=f"sim_{self.sim_user_key}@simulator.local",
            hashed_password="SIMULATOR_USER_NO_LOGIN",
            full_name=f"Sim {config.anchor_type.value} {self.sim_user_key}",
            is_active=True,
            is_verified=False,
            diabetes_type="Type 1",
            timezone="UTC",
            target_range_low=70,
            target_range_high=180,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # ── Health Metrics ──

    async def write_glucose_metrics(
        self,
        user_id: int,
        readings: list[dict],
    ) -> list[HealthMetric]:
        """Write CGM readings as BLOOD_GLUCOSE metrics.

        Args:
            user_id: Sim user's DB user ID.
            readings: List of {timestamp, glucose_value, trend} dicts.

        Returns:
            Created HealthMetric instances.
        """
        batch = []
        created: list[HealthMetric] = []
        for r in readings:
            batch.append(
                HealthMetricCreate(
                    type=MetricType.BLOOD_GLUCOSE,
                    value=r["glucose_value"],
                    unit="mg/dL",
                    measured_at=r["timestamp"],
                    source="simulator",
                    provider_id=f"sim_{self.sim_user_key}_{r['timestamp'].isoformat()}",
                    meta={
                        "sim_run_id": self.sim_run_id,
                        "sim_user_key": self.sim_user_key,
                        "trend": r.get("trend"),
                        "trend_rate": r.get("trend_rate"),
                        "delta": r.get("delta"),
                    },
                )
            )
            # Chunk at 500 to stay under the 1000 limit
            if len(batch) >= 500:
                batch_data = BatchHealthMetricCreate(metrics=batch, source="simulator")
                chunk_created, _ = await self.metric_service.create_batch(user_id, batch_data)
                created.extend(chunk_created)
                batch = []

        if batch:
            batch_data = BatchHealthMetricCreate(metrics=batch, source="simulator")
            chunk_created, _ = await self.metric_service.create_batch(user_id, batch_data)
            created.extend(chunk_created)
        return created

    async def write_meal_metrics(
        self,
        user_id: int,
        meals: list[dict],
    ) -> list[HealthMetric]:
        """Write meal events as CARBS / FAT / PROTEIN / CALORIES metrics.

        Args:
            user_id: Sim user's DB user ID.
            meals: Meal event dicts from DailySchedule.

        Returns:
            Created HealthMetric instances.
        """
        metrics = []
        for meal in meals:
            for mtype, field, unit in [
                (MetricType.CARBS, "carbs_grams", "g"),
                (MetricType.FAT, "fat_grams", "g"),
                (MetricType.PROTEIN, "protein_grams", "g"),
                (MetricType.CALORIES, "calories", "kcal"),
            ]:
                value = meal.get(field)
                if value is not None and value > 0:
                    metric = await self.metric_service.create(
                        user_id,
                        HealthMetricCreate(
                            type=mtype,
                            value=float(value),
                            unit=unit,
                            measured_at=meal["timestamp"],
                            source="simulator",
                            provider_id=f"sim_{self.sim_user_key}_meal_{meal['timestamp'].isoformat()}_{mtype.value}",
                            meta={
                                "sim_run_id": self.sim_run_id,
                                "sim_user_key": self.sim_user_key,
                                "meal_type": meal.get("type"),
                                "description": meal.get("description"),
                            },
                        ),
                    )
                    metrics.append(metric)
        return metrics

    async def write_insulin_metrics(
        self,
        user_id: int,
        insulin_events: list[dict],
    ) -> list[HealthMetric]:
        """Write insulin events as INSULIN / INSULIN_BOLUS / INSULIN_BASAL metrics.

        Args:
            user_id: Sim user's DB user ID.
            insulin_events: Insulin event dicts.

        Returns:
            Created HealthMetric instances.
        """
        metrics = []
        for ins in insulin_events:
            mtype = MetricType.INSULIN_BASAL if ins["type"] == "basal" else MetricType.INSULIN_BOLUS
            metric = await self.metric_service.create(
                user_id,
                HealthMetricCreate(
                    type=mtype,
                    value=float(ins["units"]),
                    unit="units",
                    measured_at=ins["timestamp"],
                    source="simulator",
                    provider_id=f"sim_{self.sim_user_key}_insulin_{ins['timestamp'].isoformat()}",
                    meta={
                        "sim_run_id": self.sim_run_id,
                        "sim_user_key": self.sim_user_key,
                        "insulin_type": ins["type"],
                        "description": ins.get("description"),
                    },
                ),
            )
            metrics.append(metric)
        return metrics

    async def write_exercise_metrics(
        self,
        user_id: int,
        exercise_events: list[dict],
    ) -> list[HealthMetric]:
        """Write exercise events as EXERCISE_MINUTES metrics.

        Args:
            user_id: Sim user's DB user ID.
            exercise_events: Exercise event dicts.

        Returns:
            Created HealthMetric instances.
        """
        metrics = []
        for ex in exercise_events:
            metric = await self.metric_service.create(
                user_id,
                HealthMetricCreate(
                    type=MetricType.EXERCISE_MINUTES,
                    value=float(ex["duration_minutes"]),
                    unit="minutes",
                    measured_at=ex["timestamp"],
                    ended_at=ex["timestamp"] + __import__("datetime").timedelta(minutes=ex["duration_minutes"]),
                    source="simulator",
                    provider_id=f"sim_{self.sim_user_key}_exercise_{ex['timestamp'].isoformat()}",
                    meta={
                        "sim_run_id": self.sim_run_id,
                        "sim_user_key": self.sim_user_key,
                        "intensity": ex.get("intensity"),
                        "exercise_type": ex.get("type"),
                    },
                ),
            )
            metrics.append(metric)
        return metrics

    async def write_sleep_metrics(
        self,
        user_id: int,
        sleep_start: Optional[datetime],
        sleep_end: Optional[datetime],
    ) -> list[HealthMetric]:
        """Write sleep events as SLEEP_HOURS metrics.

        Args:
            user_id: Sim user's DB user ID.
            sleep_start: Sleep start time.
            sleep_end: Sleep end time.

        Returns:
            Created HealthMetric instances.
        """
        if not sleep_start or not sleep_end:
            return []
        hours = (sleep_end - sleep_start).total_seconds() / 3600
        if hours <= 0:
            return []
        metric = await self.metric_service.create(
            user_id,
            HealthMetricCreate(
                type=MetricType.SLEEP_HOURS,
                value=round(hours, 2),
                unit="hours",
                measured_at=sleep_start,
                ended_at=sleep_end,
                source="simulator",
                provider_id=f"sim_{self.sim_user_key}_sleep_{sleep_start.isoformat()}",
                meta={
                    "sim_run_id": self.sim_run_id,
                    "sim_user_key": self.sim_user_key,
                },
            ),
        )
        return [metric]

    # ── Legacy Table Writes ──

    async def write_legacy_glucose(
        self,
        user_id: int,
        readings: list[dict],
    ) -> int:
        """Write CGM readings to tbl_glucose_readings (legacy).

        Args:
            user_id: Sim user's DB user ID.
            readings: List of {timestamp, glucose_value, trend} dicts.

        Returns:
            Count of written readings.
        """
        count = 0
        for r in readings:
            db_reading = GlucoseReading(
                user_id=user_id,
                timestamp=r["timestamp"],
                glucose_value=r["glucose_value"],
                glucose_units="mg/dL",
                reading_type="sensor",
                source="simulator",
                trend=r.get("trend"),
                trend_rate=r.get("trend_rate"),
            )
            self.db.add(db_reading)
            count += 1
            if count % 500 == 0:
                await self.db.flush()
        await self.db.flush()
        logger.info(f"Wrote {count} legacy glucose readings for user {user_id}")
        return count

    async def write_legacy_events(
        self,
        user_id: int,
        daily_schedules: list,
    ) -> int:
        """Write context events to tbl_context_events (legacy).

        Args:
            user_id: Sim user's DB user ID.
            daily_schedules: List of DailySchedule objects.

        Returns:
            Count of written events.
        """
        count = 0
        for schedule in daily_schedules:
            for meal in schedule.meals:
                self.db.add(ContextEvent(
                    user_id=user_id,
                    event_type="meal",
                    event_subtype=meal["type"],
                    timestamp=meal["timestamp"],
                    description=meal.get("description", "Meal"),
                    carbs_grams=meal.get("carbs_grams"),
                    fat_grams=meal.get("fat_grams"),
                    protein_grams=meal.get("protein_grams"),
                    calories=meal.get("calories"),
                ))
                count += 1

            for ins in schedule.insulin:
                self.db.add(ContextEvent(
                    user_id=user_id,
                    event_type="insulin",
                    event_subtype=ins["type"],
                    timestamp=ins["timestamp"],
                    description=ins.get("description", "Insulin"),
                    insulin_units=ins.get("units"),
                ))
                count += 1

            for ex in schedule.exercise:
                self.db.add(ContextEvent(
                    user_id=user_id,
                    event_type="exercise",
                    event_subtype=ex.get("type"),
                    timestamp=ex["timestamp"],
                    duration=ex.get("duration_minutes"),
                    description=ex.get("description", "Exercise"),
                    intensity=ex.get("intensity"),
                ))
                count += 1

            await self.db.flush()

        logger.info(f"Wrote {count} legacy events for user {user_id}")
        return count
