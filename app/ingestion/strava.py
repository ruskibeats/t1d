"""Strava health data ingestion service.

OAuth2 data sync for Strava activities.
Maps activity types to MetricType values (exercise minutes, distance, heart rate).
"""

from datetime import datetime, timezone
from typing import Any

from app.metrics.schemas import HealthMetricCreate
from app.metrics.types import MetricType


class StravaIngestionService:
    """Service for fetching and normalizing Strava activity data."""

    BASE_URL = "https://www.strava.com/api/v3"

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    @staticmethod
    def authorize_url(client_id: str, redirect_uri: str) -> str:
        return (
            f"https://www.strava.com/oauth/authorize?"
            f"client_id={client_id}&redirect_uri={redirect_uri}"
            f"&response_type=code&approval_prompt=auto"
            f"&scope=read,activity:read_all,profile:read_all"
        )

    @staticmethod
    def token_exchange_payload(code: str, client_id: str, client_secret: str) -> dict:
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }

    def parse_activities(self, activities: list[dict]) -> list[HealthMetricCreate]:
        results = []
        for act in activities:
            start = act.get("start_date", datetime.now(timezone.utc).isoformat())
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            duration = act.get("moving_time", 0) / 60  # seconds → minutes
            act_id = str(act.get("id", ""))

            results.append(HealthMetricCreate(
                type=MetricType.EXERCISE_MINUTES,
                value=duration,
                unit="minutes",
                measured_at=start_dt,
                source="strava",
                provider_id=act_id,
            ))

            if "distance" in act and act["distance"]:
                dist_km = act["distance"] / 1000
                results.append(HealthMetricCreate(
                    type=MetricType.DISTANCE_KM,
                    value=dist_km,
                    unit="km",
                    measured_at=start_dt,
                    source="strava",
                    provider_id=act_id,
                ))

            if "average_heartrate" in act and act["average_heartrate"]:
                results.append(HealthMetricCreate(
                    type=MetricType.HEART_RATE,
                    value=float(act["average_heartrate"]),
                    unit="bpm",
                    measured_at=start_dt,
                    source="strava",
                    provider_id=act_id,
                ))

            if "total_elevation_gain" in act and act["total_elevation_gain"]:
                results.append(HealthMetricCreate(
                    type=MetricType.FLOORS_CLIMBED,
                    value=float(act["total_elevation_gain"]),
                    unit="meters",
                    measured_at=start_dt,
                    source="strava",
                    provider_id=act_id,
                ))

            if "calories" in act and act["calories"]:
                results.append(HealthMetricCreate(
                    type=MetricType.CALORIES,
                    value=float(act["calories"]),
                    unit="kcal",
                    measured_at=start_dt,
                    source="strava",
                    provider_id=act_id,
                ))
        return results
