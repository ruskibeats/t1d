"""Ingestion package for external health data providers.

Provides services for parsing and normalizing data from:
- Garmin
- Fitbit
- Withings
- Strava
- Polar
"""

from app.ingestion.garmin import GarminIngestionService
from app.ingestion.fitbit import FitbitIngestionService
from app.ingestion.withings import WithingsIngestionService
from app.ingestion.strava import StravaIngestionService
from app.ingestion.polar import PolarIngestionService

__all__ = ["GarminIngestionService", "FitbitIngestionService",
           "WithingsIngestionService", "StravaIngestionService",
           "PolarIngestionService"]