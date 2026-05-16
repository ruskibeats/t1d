"""Withings health data ingestion service.

Handles Withings notification API webhooks and data retrieval.
Maps weight, heart rate, and sleep data to HealthMetricCreate.
"""

from datetime import datetime, timezone
from typing import Any

from app.metrics.schemas import HealthMetricCreate
from app.metrics.types import MetricType


class WithingsIngestionService:
    """Service for processing Withings webhook notifications and syncing data."""

    BASE_URL = "https://wbsapi.withings.net"

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    def handle_notification(self, payload: dict) -> list[HealthMetricCreate]:
        """Process a Withings webhook notification."""
        results = []
        body = payload.get("body", payload)

        # Weight measurement
        if "weight" in body:
            results.append(HealthMetricCreate(
                type=MetricType.WEIGHT,
                value=float(body["weight"]),
                unit="kg",
                measured_at=datetime.now(timezone.utc),
                source="withings",
            ))
        # Heart rate
        if "heart_rate" in body:
            results.append(HealthMetricCreate(
                type=MetricType.HEART_RATE,
                value=float(body["heart_rate"]),
                unit="bpm",
                measured_at=datetime.now(timezone.utc),
                source="withings",
            ))
        return results

    def parse_measurements(self, measuregrps: list[dict]) -> list[HealthMetricCreate]:
        """Parse Withings measurement groups into HealthMetricCreate objects."""
        results = []
        for group in measuregrps:
            date = group.get("date", datetime.now().timestamp())
            recorded_at = datetime.fromtimestamp(date, tz=timezone.utc)
            for measure in group.get("measures", []):
                metric_type, value, unit = self._map_measure(measure)
                if metric_type:
                    results.append(HealthMetricCreate(
                        type=metric_type,
                        value=value,
                        unit=unit,
                        measured_at=recorded_at,
                        source="withings",
                    ))
        return results

    def parse_sleep(self, series: list[dict]) -> list[HealthMetricCreate]:
        results = []
        for entry in series:
            start = entry.get("startdate", datetime.now().timestamp())
            end = entry.get("enddate", start)
            duration_hours = (end - start) / 3600
            results.append(HealthMetricCreate(
                type=MetricType.SLEEP_HOURS,
                value=duration_hours,
                unit="hours",
                measured_at=datetime.fromtimestamp(start, tz=timezone.utc),
                source="withings",
                provider_id=str(entry.get("id", "")),
            ))
            if "data" in entry:
                results.append(HealthMetricCreate(
                    type=MetricType.SLEEP_SCORE,
                    value=float(entry.get("data", {}).get("score", 0)),
                    unit="score",
                    measured_at=datetime.fromtimestamp(start, tz=timezone.utc),
                    source="withings",
                ))
        return results

    @staticmethod
    def _map_measure(measure: dict) -> tuple[MetricType | None, float, str]:
        type_map = {
            1: (MetricType.WEIGHT, "kg"),
            4: (MetricType.WEIGHT, "kg"),  # height not available as MetricType
            8: (MetricType.BODY_FAT_PERCENT, "%"),
            5: (MetricType.BODY_FAT_PERCENT, "%"),  # fat free mass
            11: (MetricType.HEART_RATE, "bpm"),
            12: (MetricType.HEART_RATE, "bpm"),  # resting heart rate
            54: (MetricType.BLOOD_PRESSURE_SYSTOLIC, "mmHg"),
            55: (MetricType.BLOOD_PRESSURE_DIASTOLIC, "mmHg"),
            73: (MetricType.WEIGHT, "kg"),  # lean mass
            76: (MetricType.BODY_FAT_PERCENT, "%"),  # muscle mass
            77: (MetricType.WEIGHT, "kg"),  # bone mass
            88: (MetricType.CALORIES, "kcal"),  # basal metabolism
        }
        measure_type = measure.get("type", 0)
        entry = type_map.get(measure_type)
        if not entry:
            return None, 0, ""
        metric_type, unit = entry
        value = measure.get("value", 0) * (10 ** measure.get("unit", 0))
        return metric_type, value, unit
