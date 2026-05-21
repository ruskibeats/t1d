import csv
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, GlucoseReading, ContextEvent
from app.metrics.schemas import HealthMetricCreate
from app.metrics.service import HealthMetricService
from app.metrics.types import MetricType
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class SyntheticIngestionMapper:
    """Maps Synthea CSV output to T1D domain models."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.metric_service = HealthMetricService(db)

    async def map_patient(self, row: dict) -> User:
        """Maps patient CSV row to User model."""
        # Synthea row structure example: 
        # Id,BIRTHDATE,DEATHDATE,SSN,DRIVERS,PASSPORT,PREFIX,FIRST,LAST,SUFFIX,MAIDEN,MARITAL,RACE,ETHNICITY,GENDER,BIRTHPLACE,ADDRESS
        
        user = User(
            email=f"{row['FIRST']}.{row['LAST']}_{row['Id']}@example.com".lower(),
            hashed_password="dummy_password_for_synthetic_users",
            full_name=f"{row['FIRST']} {row['LAST']}",
            is_active=True,
            is_verified=True,
            diabetes_type="Type 1" # Biased population
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def map_observation(self, row: dict, user_id: int) -> None:
        """Maps observation CSV row to HealthMetric (e.g., Blood Glucose)."""
        # Synthea row structure example:
        # DATE,PATIENT,ENCOUNTER,CODE,DESCRIPTION,VALUE,UNITS,TYPE
        
        if row['DESCRIPTION'] in ['Glucose', 'Blood Glucose']:
            try:
                metric = HealthMetricCreate(
                    type=MetricType.BLOOD_GLUCOSE,
                    value=float(row['VALUE']),
                    unit=row['UNITS'],
                    measured_at=datetime.fromisoformat(row['DATE']),
                    source="synthea_import"
                )
                await self.metric_service.create(user_id, metric)
            except (ValueError, KeyError) as e:
                logger.warning(f"Error mapping observation: {e}")

    async def map_condition(self, row: dict, user_id: int) -> None:
        """Maps condition CSV row to ContextEvent (e.g., Diabetes diagnosis)."""
        # Synthea row structure example:
        # START,STOP,PATIENT,ENCOUNTER,CODE,DESCRIPTION
        
        if "diabetes" in row['DESCRIPTION'].lower():
            try:
                event = ContextEvent(
                    user_id=user_id,
                    event_type="condition",
                    event_subtype=row['DESCRIPTION'],
                    timestamp=datetime.fromisoformat(row['START']),
                    description=row['DESCRIPTION']
                )
                self.db.add(event)
                await self.db.commit()
            except (ValueError, KeyError) as e:
                logger.warning(f"Error mapping condition: {e}")
