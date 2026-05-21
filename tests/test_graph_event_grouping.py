"""Tests for graph event grouping and same-event edge deduplication."""

import pytest
from datetime import datetime, timezone

from app.metrics.service import HealthMetricService
from app.metrics.schemas import HealthMetricCreate
from app.metrics.graph_service import HealthGraphService
from app.metrics.types import GraphEdgeType, MetricType


@pytest.mark.asyncio
async def test_event_group_id_queries(db_session, test_user):
    """Test querying metrics by event_group_id."""
    db = db_session
    user_id = test_user.id
    
    service = HealthMetricService(db)
    
    # Create metrics with same event_group_id
    for i in range(3):
        await service.create(
            user_id,
            HealthMetricCreate(
                type=MetricType.CARBS if i == 0 else (MetricType.PROTEIN if i == 1 else MetricType.FAT),
                value=30.0 + i * 10,
                unit="g",
                measured_at=datetime.now(timezone.utc),
                source="test",
                event_group_id="meal-123",
            ),
        )
    
    # Query by event_group_id using SQLAlchemy
    from sqlalchemy import select
    from app.metrics.models import HealthMetric
    result = await db.execute(
        select(HealthMetric).where(
            HealthMetric.user_id == user_id,
            HealthMetric.event_group_id == "meal-123"
        )
    )
    metrics = result.scalars().all()
    assert len(metrics) >= 3


@pytest.mark.asyncio
async def test_same_event_edge_deduplication(db_session, test_user):
    """Test that same_event_as edges are deduplicated."""
    db = db_session
    user_id = test_user.id
    service = HealthGraphService(db)
    
    # Create two metrics with same event_group_id
    metric1 = await HealthMetricService(db).create(
        user_id, HealthMetricCreate(
            type=MetricType.CARBS, value=50, unit="g",
            measured_at=datetime.now(timezone.utc), source="test",
            event_group_id="dedup-test",
        ),
    )
    metric2 = await HealthMetricService(db).create(
        user_id, HealthMetricCreate(
            type=MetricType.FAT, value=20, unit="g",
            measured_at=datetime.now(timezone.utc), source="test",
            event_group_id="dedup-test",
        ),
    )
    
    # Create edge manually
    from app.metrics.schemas import HealthMetricEdgeCreate
    edge1 = await service.upsert_edge(
        user_id, HealthMetricEdgeCreate(
            source_metric_id=metric1.id,
            target_metric_id=metric2.id,
            edge_type=GraphEdgeType.SAME_EVENT_AS,
            confidence=1.0,
            algorithm="test",
        ),
    )
    
    # Try to create duplicate edge (should update existing, not create new)
    edge2 = await service.upsert_edge(
        user_id, HealthMetricEdgeCreate(
            source_metric_id=metric1.id,
            target_metric_id=metric2.id,
            edge_type=GraphEdgeType.SAME_EVENT_AS,
            confidence=0.9,
            algorithm="test",
        ),
    )
    
    assert edge1.id == edge2.id


@pytest.mark.asyncio
async def test_link_event_group_creates_edges(db_session, test_user):
    """Test link_event_group creates all pairwise edges."""
    db = db_session
    user_id = test_user.id
    
    # Create 4 metrics with same event_group_id
    metrics = []
    for i in range(4):
        m = await HealthMetricService(db).create(
            user_id, HealthMetricCreate(
                type=[MetricType.CARBS, MetricType.PROTEIN, MetricType.FAT, MetricType.CALORIES][i],
                value=50.0 + i * 10,
                unit="g" if i < 3 else "kcal",
                measured_at=datetime.now(timezone.utc),
                source="test",
                event_group_id="multi-meal",
            ),
        )
        metrics.append(m)
    
    service = HealthGraphService(db)
    edges = await service.link_event_group(user_id, "multi-meal")
    
    # 4 metrics should create 6 pairwise edges (combination of 4 taken 2 at a time)
    assert len(edges) == 6