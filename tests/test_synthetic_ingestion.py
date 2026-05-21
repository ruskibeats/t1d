import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.synthetic_ingestion import SyntheticIngestionMapper
from app.db.models import User, ContextEvent
from app.metrics.types import MetricType

@pytest.mark.asyncio
async def test_map_patient(db_session):
    mapper = SyntheticIngestionMapper(db_session)
    # Synthea mock row
    row = {
        'Id': '123',
        'FIRST': 'John',
        'LAST': 'Doe'
    }
    user = await mapper.map_patient(row)
    assert user.full_name == 'John Doe'
    assert user.email == 'john.doe_123@example.com'

@pytest.mark.asyncio
async def test_map_observation(db_session, test_user):
    mapper = SyntheticIngestionMapper(db_session)
    row = {
        'DATE': '2026-05-20T10:00:00',
        'DESCRIPTION': 'Glucose',
        'VALUE': '150',
        'UNITS': 'mg/dL'
    }
    await mapper.map_observation(row, test_user.id)
    
    from app.metrics.service import HealthMetricService
    from app.metrics.schemas import HealthMetricQuery
    
    service = HealthMetricService(db_session)
    metrics = await service.query(test_user.id, HealthMetricQuery(
        start_time=datetime(2026, 5, 20),
        end_time=datetime(2026, 5, 21),
        types=[MetricType.BLOOD_GLUCOSE]
    ))
    assert len(metrics) == 1
    assert metrics[0].value == 150.0

from sqlalchemy import select
@pytest.mark.asyncio
async def test_map_condition(db_session, test_user):
    mapper = SyntheticIngestionMapper(db_session)
    row = {
        'START': '2026-05-20T10:00:00',
        'DESCRIPTION': 'Diabetes Mellitus'
    }
    await mapper.map_condition(row, test_user.id)
    
    result = await db_session.execute(
        select(ContextEvent).filter(ContextEvent.user_id == test_user.id)
    )
    events = result.scalars().all()
    assert len(events) == 1
    assert "diabetes" in events[0].description.lower()
