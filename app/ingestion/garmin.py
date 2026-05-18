"""Garmin health data ingestion service.

Parses and normalizes Garmin Connect data for T1D Companion.
Supports activities, sleep, and body composition data.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.logging_config import get_logger
from app.metrics.schemas import BatchHealthMetricCreate, HealthMetricCreate
from app.metrics.service import HealthMetricService
from app.metrics.types import MetricType

logger = get_logger(__name__)


class GarminIngestionService:
    """Service for parsing Garmin Connect data.

    Converts Garmin's native formats to T1D Companion's normalized
    HealthMetric schema. Each sub-metric is emitted as a separate
    HealthMetricCreate with its own MetricType.
    """

    def __init__(self, metric_service: HealthMetricService):
        self.service = metric_service
        self.logger = logger

    def parse_activity(
        self,
        activity_data: dict[str, Any],
    ) -> list[HealthMetricCreate]:
        """Parse a Garmin activity into individual health metrics.

        Args:
            activity_data: Raw Garmin activity JSON

        Returns:
            List of HealthMetricCreate objects
        """
        metrics: list[HealthMetricCreate] = []

        start_time = datetime.fromisoformat(
            activity_data.get("startTime", datetime.now(timezone.utc).isoformat())
        )
        duration_min = activity_data.get("duration", 0) / 60
        duration_s = activity_data.get("duration", 0)
        calories = activity_data.get("calories", 0)
        heart_rate_avg = activity_data.get("averageHeartRate")
        distance_km = activity_data.get("distance", 0) / 1000
        activity_id = str(activity_data.get("activityId", "")) or str(activity_data.get("startTime", ""))

        # Each Garmin activity is a distinct event – assign an event_group_id for all its metrics
        activity_group_id = str(__import__('uuid').uuid4())
        metrics.append(HealthMetricCreate(
            type=MetricType.EXERCISE_MINUTES,
            value=duration_min,
            unit="minutes",
            measured_at=start_time,
            source="garmin",
            provider_id=activity_id,
            event_group_id=activity_group_id,
        ))

        if calories:
            metrics.append(HealthMetricCreate(
                type=MetricType.CALORIES,
                value=float(calories),
                unit="kcal",
                measured_at=start_time,
                source="garmin",
                provider_id=activity_id,
                event_group_id=activity_group_id,
            ))

        if heart_rate_avg:
            metrics.append(HealthMetricCreate(
                type=MetricType.HEART_RATE,
                value=float(heart_rate_avg),
                unit="bpm",
                measured_at=start_time,
                source="garmin",
                provider_id=activity_id,
                event_group_id=activity_group_id,
            ))

        if distance_km:
            metrics.append(HealthMetricCreate(
                type=MetricType.DISTANCE_KM,
                value=distance_km,
                unit="km",
                measured_at=start_time,
                source="garmin",
                provider_id=activity_id,
                event_group_id=activity_group_id,
            ))

        self.logger.info(f"Parsed Garmin activity: {duration_min}min, {len(metrics)} metrics")
        return metrics

    def parse_sleep(
        self,
        sleep_data: dict[str, Any],
    ) -> list[HealthMetricCreate]:
        """Parse Garmin sleep data into individual metrics.

        Args:
            sleep_data: Raw Garmin sleep JSON

        Returns:
            List of HealthMetricCreate objects
        """
        metrics: list[HealthMetricCreate] = []

        start_time = datetime.fromisoformat(sleep_data.get("startTime", datetime.now(timezone.utc).isoformat()))
        end_time = datetime.fromisoformat(sleep_data.get("endTime", start_time.isoformat()))
        duration_hours = (end_time - start_time).total_seconds() / 3600
        sleep_id = str(sleep_data.get("sleepId", "")) or str(sleep_data.get("startTime", ""))
        # Each Garmin sleep event is a distinct group – assign a shared event_group_id
        sleep_group_id = str(__import__('uuid').uuid4())

        metrics.append(HealthMetricCreate(
            type=MetricType.SLEEP_HOURS,
            value=round(duration_hours, 2),
            unit="hours",
            measured_at=start_time,
            source="garmin",
            provider_id=sleep_id,
            event_group_id=sleep_group_id,
        ))

        stages = sleep_data.get("stages", {})
        stage_map = {
            "deepMinutes": (MetricType.SLEEP_DEEP, 60),
            "lightMinutes": (MetricType.SLEEP_LIGHT, 60),
            "remMinutes": (MetricType.SLEEP_REM, 60),
            "awakeMinutes": (MetricType.SLEEP_AWAKE, 1),
        }
        for key, (mtype, divisor) in stage_map.items():
            val = stages.get(key, 0)
            if val:
                metrics.append(HealthMetricCreate(
                    type=mtype,
                    value=val / divisor,
                    unit="hours" if divisor == 60 else "minutes",
                    measured_at=start_time,
                    source="garmin",
                    provider_id=sleep_id,
                    event_group_id=sleep_group_id,
                ))

        self.logger.info(f"Parsed Garmin sleep: {duration_hours}h, {len(metrics)} metrics")
        return metrics

    def parse_body_composition(
        self,
        body_data: dict[str, Any],
    ) -> list[HealthMetricCreate]:
        """Parse Garmin body composition data.

        Args:
            body_data: Raw Garmin body composition JSON

        Returns:
            List of HealthMetricCreate objects
        """
        metrics: list[HealthMetricCreate] = []

        timestamp = datetime.fromisoformat(body_data.get("timestamp", datetime.now(timezone.utc).isoformat()))
        body_id = str(body_data.get("bodyCompositionId", "")) or str(body_data.get("timestamp", ""))
        # Each Garmin body composition entry is a distinct event – assign a group ID
        body_group_id = str(__import__('uuid').uuid4())

        weight = body_data.get("weight")
        if weight:
            metrics.append(HealthMetricCreate(
                type=MetricType.WEIGHT,
                value=float(weight),
                unit="kg",
                measured_at=timestamp,
                source="garmin",
                provider_id=body_id,
                event_group_id=body_group_id,
            ))

        body_fat = body_data.get("bodyFatPercent")
        if body_fat:
            metrics.append(HealthMetricCreate(
                type=MetricType.BODY_FAT_PERCENT,
                value=float(body_fat),
                unit="%",
                measured_at=timestamp,
                source="garmin",
                provider_id=body_id,
                event_group_id=body_group_id,
            ))

        muscle = body_data.get("muscleMass")
        if muscle:
            metrics.append(HealthMetricCreate(
                type=MetricType.LEAN_MASS,
                value=float(muscle),
                unit="kg",
                measured_at=timestamp,
                source="garmin",
                provider_id=body_id,
                event_group_id=body_group_id,
            ))

        self.logger.info(f"Parsed Garmin body composition: {len(metrics)} metrics")
        return metrics

    async def ingest_webhook(
        self,
        user_id: int,
        payload: dict[str, Any],
    ) -> dict[str, int]:
        """Process a Garmin webhook payload via batch insert.

        Args:
            user_id: User ID
            payload: Raw webhook JSON

        Returns:
            Dict with counts of ingested metrics
        """
        all_metrics: list[HealthMetricCreate] = []

        for activity in payload.get("activities", []):
            all_metrics.extend(self.parse_activity(activity))

        for sleep in payload.get("sleep", []):
            all_metrics.extend(self.parse_sleep(sleep))

        for body in payload.get("bodyComposition", []):
            all_metrics.extend(self.parse_body_composition(body))

        if all_metrics:
            batch = BatchHealthMetricCreate(metrics=all_metrics)
            created, skipped = await self.service.create_batch(user_id, batch)
            return {"created": len(created), "skipped": skipped}

        return {"created": 0, "skipped": 0}
