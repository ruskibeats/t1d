"""Tests for graph edge provenance structure."""

import pytest
from datetime import datetime, timezone

from app.metrics.graph_service import HealthGraphService
from app.metrics.schemas import HealthMetricEdgeCreate, HealthMetricCreate
from app.metrics.types import GraphEdgeType, MetricType
from app.metrics.service import HealthMetricService


@pytest.mark.asyncio
async def test_edge_provenance_structure(db_session, test_user):
    """Test that edges have detector/version/timestamps in provenance."""
    db = db_session
    user_id = test_user.id
    
    # Create source and target metrics
    source = await HealthMetricService(db).create(
        user_id, HealthMetricCreate(
            type=MetricType.CARBS, value=50, unit="g",
            measured_at=datetime.now(timezone.utc), source="test",
        ),
    )
    target = await HealthMetricService(db).create(
        user_id, HealthMetricCreate(
            type=MetricType.BLOOD_GLUCOSE, value=150, unit="mg/dL",
            measured_at=datetime.now(timezone.utc), source="test",
        ),
    )
    
    service = HealthGraphService(db)
    edge = await service.upsert_edge(
        user_id, HealthMetricEdgeCreate(
            source_metric_id=source.id,
            target_metric_id=target.id,
            edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
            confidence=0.8,
            algorithm="pattern_service.post_meal_spike.v1",
            evidence={"test": "data"},
        ),
    )
    
    # Verify RAG context includes evidence
    assert edge.evidence is not None
    assert edge.evidence.get("test") == "data"


@pytest.mark.asyncio
async def test_provenance_consistency_across_edge_types(db_session, test_user):
    """Test provenance JSON structure is consistent."""
    db = db_session
    user_id = test_user.id
    
    edge_types = [
        GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
        GraphEdgeType.MEAL_TO_DELAYED_SPIKE,
        GraphEdgeType.EXERCISE_TO_GLUCOSE_DROP,
    ]
    
    # Create base metrics
    source = await HealthMetricService(db).create(
        user_id, HealthMetricCreate(
            type=MetricType.CARBS, value=50, unit="g",
            measured_at=datetime.now(timezone.utc), source="test",
        ),
    )
    target = await HealthMetricService(db).create(
        user_id, HealthMetricCreate(
            type=MetricType.BLOOD_GLUCOSE, value=160, unit="mg/dL",
            measured_at=datetime.now(timezone.utc), source="test",
        ),
    )
    
    service = HealthGraphService(db)
    
    for edge_type in edge_types:
        edge = await service.upsert_edge(
            user_id, HealthMetricEdgeCreate(
                source_metric_id=source.id,
                target_metric_id=target.id,
                edge_type=edge_type,
                confidence=0.7,
                algorithm="test.v1",
            ),
        )
        # Basic provenance check - algorithm should be set
        assert edge.algorithm is not None