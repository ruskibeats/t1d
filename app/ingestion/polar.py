"""Polar health data ingestion service.

Polar AccessLink API v3 for training sessions and sleep data.
"""

from datetime import datetime, timezone
from typing import Any

from app.metrics.schemas import HealthMetricCreate
from app.metrics.types import MetricType


class PolarIngestionService:
    """Service for fetching and normalizing Polar data via AccessLink API v3."""

    BASE_URL = "https://www.polaraccesslink.com/v3"

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    def parse_training_sessions(self, sessions: list[dict]) -> list[HealthMetricCreate]:
        results = []
        for session in sessions:
            start = session.get("start_time", datetime.now(timezone.utc).isoformat())
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if "T" in start else datetime.now(timezone.utc)
            duration = session.get("duration", 0) / 60  # seconds → minutes
            session_id = str(session.get("id", ""))

            results.append(HealthMetricCreate(
                type=MetricType.EXERCISE_MINUTES,
                value=duration,
                unit="minutes",
                measured_at=start_dt,
                source="polar",
                provider_id=session_id,
            ))

            if "calories" in session:
                results.append(HealthMetricCreate(
                    type=MetricType.CALORIES,
                    value=float(session["calories"]),
                    unit="kcal",
                    measured_at=start_dt,
                    source="polar",
                    provider_id=session_id,
                ))

            if "heart_rate" in session and "average" in session["heart_rate"]:
                results.append(HealthMetricCreate(
                    type=MetricType.HEART_RATE,
                    value=float(session["heart_rate"]["average"]),
                    unit="bpm",
                    measured_at=start_dt,
                    source="polar",
                    provider_id=session_id,
                ))
        return results

    def parse_sleep(self, sleep_data: list[dict]) -> list[HealthMetricCreate]:
        results = []
        for entry in sleep_data:
            start = entry.get("start_time", datetime.now(timezone.utc).isoformat())
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if "T" in start else datetime.now(timezone.utc)
            duration = entry.get("duration", 0) / 3600  # seconds → hours
            entry_id = str(entry.get("id", ""))

            results.append(HealthMetricCreate(
                type=MetricType.SLEEP_HOURS,
                value=duration,
                unit="hours",
                measured_at=start_dt,
                source="polar",
                provider_id=entry_id,
            ))

            if "hypnogram" in entry:
                for stage in entry.get("hypnogram", []):
                    stage_type = stage.get("stage", "").lower()
                    stage_duration = stage.get("duration", 0) / 3600
                    metric_map = {
                        "deep": MetricType.SLEEP_DEEP,
                        "rem": MetricType.SLEEP_REM,
                        "light": MetricType.SLEEP_LIGHT,
                        "awake": MetricType.SLEEP_AWAKE,
                    }
                    mapped = metric_map.get(stage_type)
                    if mapped:
                        results.append(HealthMetricCreate(
                            type=mapped,
                            value=stage_duration,
                            unit="hours",
                            measured_at=start_dt,
                            source="polar",
                            provider_id=entry_id,
                        ))
        return results
