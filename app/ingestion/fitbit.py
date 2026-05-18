"""Fitbit health data ingestion service.

OAuth2 data sync for Fitbit activities, sleep, and heart rate.
Maps Fitbit API responses to the unified HealthMetricCreate format.
"""

from datetime import datetime, timezone
from typing import Any

from app.metrics.schemas import HealthMetricCreate
from app.metrics.types import MetricType


class FitbitIngestionService:
    """Service for fetching and normalizing Fitbit data."""

    BASE_URL = "https://api.fitbit.com/1/user/-"

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    @staticmethod
    def authorize_url(client_id: str, redirect_uri: str) -> str:
        return (
            f"https://www.fitbit.com/oauth2/authorize?"
            f"response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
            f"&scope=activity+heartrate+location+nutrition+oxygen_saturation+sleep+weight"
        )

    @staticmethod
    def token_exchange_payload(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        return {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }

    def parse_activities(self, activities: list[dict]) -> list[HealthMetricCreate]:
        results = []
        now = datetime.now(timezone.utc)
        for act in activities:
            start = act.get("startTime", now.isoformat())
            duration = act.get("duration", 0) / 1000 / 60  # ms → minutes
            # Generate a unique group ID for each activity event
            activity_group_id = str(__import__('uuid').uuid4())
            results.append(HealthMetricCreate(
                type=MetricType.EXERCISE_MINUTES,
                value=duration,
                unit="minutes",
                measured_at=datetime.fromisoformat(start.replace("Z", "+00:00")),
                source="fitbit",
                provider_id=act.get("logId", str(act.get("startTime", ""))),
                event_group_id=activity_group_id,
            ))
            if "calories" in act:
                results.append(HealthMetricCreate(
                    type=MetricType.CALORIES,
                    value=float(act["calories"]),
                    unit="kcal",
                    measured_at=datetime.fromisoformat(start.replace("Z", "+00:00")),
                    source="fitbit",
                    event_group_id=activity_group_id,
                ))
        return results

    def parse_sleep(self, sleep_data: dict) -> list[HealthMetricCreate]:
        results = []
        if "sleep" not in sleep_data:
            return results
        for entry in sleep_data["sleep"]:
            start = entry.get("startTime", "")
            end = entry.get("endTime", "")
            duration = entry.get("duration", 0) / 1000 / 60
            # Generate a unique group ID for each sleep event
            sleep_group_id = str(__import__('uuid').uuid4())
            results.append(HealthMetricCreate(
                type=MetricType.SLEEP_HOURS,
                value=duration / 60,
                unit="hours",
                measured_at=datetime.fromisoformat(start.replace("Z", "+00:00")),
                source="fitbit",
                provider_id=entry.get("logId", str(start)),
                event_group_id=sleep_group_id,
            ))
            if "efficiency" in entry:
                results.append(HealthMetricCreate(
                    type=MetricType.SLEEP_SCORE,
                    value=float(entry["efficiency"]),
                    unit="percent",
                    measured_at=datetime.fromisoformat(start.replace("Z", "+00:00")),
                    source="fitbit",
                    event_group_id=sleep_group_id,
                ))
        return results

    def parse_heart_rate(self, hr_data: list[dict]) -> list[HealthMetricCreate]:
        results = []
        for point in hr_data:
            timestamp = point.get("dateTime", "")
            if "value" in point:
                results.append(HealthMetricCreate(
                    type=MetricType.HEART_RATE,
                    value=float(point["value"].get("restingHeartRate", 0) if isinstance(point["value"], dict) else point["value"]),
                    unit="bpm",
                    measured_at=datetime.fromisoformat(timestamp),
                    source="fitbit",
                ))
        return results
