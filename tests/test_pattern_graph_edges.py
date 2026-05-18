"""Tests that pattern detection persists graph edges."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.db.models import ContextEvent, GlucoseReading
from app.metrics.models import HealthMetricEdge
from app.metrics.schemas import HealthMetricCreate
from app.metrics.service import HealthMetricService
from app.metrics.types import GraphEdgeType, MetricType
from app.services.pattern_service import PatternService


@pytest.mark.asyncio
async def test_post_meal_spike_detection_creates_graph_edge(db_session, test_user):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    meal_time = now - timedelta(hours=3)
    peak_time = meal_time + timedelta(hours=2)

    meal = ContextEvent(
        user_id=test_user.id,
        event_type="meal",
        description="Pizza",
        carbs_grams=80,
        timestamp=meal_time,
    )
    db_session.add(meal)
    db_session.add(
        GlucoseReading(
            user_id=test_user.id,
            glucose_value=110,
            glucose_units="mg/dL",
            timestamp=meal_time - timedelta(minutes=20),
            reading_type="sensor",
            source="dexcom",
            trend="flat",
        )
    )
    db_session.add(
        GlucoseReading(
            user_id=test_user.id,
            glucose_value=230,
            glucose_units="mg/dL",
            timestamp=peak_time,
            reading_type="sensor",
            source="dexcom",
            trend="rising",
        )
    )
    await db_session.commit()

    metric_service = HealthMetricService(db_session)
    carbs_metric = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.CARBS, value=80, unit="g", measured_at=meal_time, source="manual"),
    )
    glucose_metric = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.BLOOD_GLUCOSE, value=230, unit="mg/dL", measured_at=peak_time, source="dexcom"),
    )

    spikes = await PatternService().detect_post_meal_spikes(
        db_session,
        test_user.id,
        meal_time - timedelta(hours=1),
        peak_time + timedelta(hours=1),
    )

    assert len(spikes) == 1
    result = await db_session.execute(select(HealthMetricEdge))
    edge = result.scalar_one()
    assert edge.source_metric_id == carbs_metric.id
    assert edge.target_metric_id == glucose_metric.id
    assert edge.edge_type == GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE
    assert edge.time_delay_seconds == 7200
    assert edge.evidence["food_name"] == "Pizza"
    assert edge.evidence["glucose_rise"] == 120
