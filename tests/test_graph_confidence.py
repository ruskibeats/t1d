"""Tests for graph edge confidence component scoring."""

import pytest
from datetime import datetime, timezone

from app.metrics.graph_service import HealthGraphService
from app.metrics.schemas import HealthMetricEdgeCreate, HealthMetricCreate
from app.metrics.types import GraphEdgeType, MetricType
from app.metrics.service import HealthMetricService
from app.metrics.confidence_scoring import ConfidenceComponents, categorize_confidence


@pytest.mark.asyncio
async def test_confidence_components_json(db_session, test_user):
    """Test confidence_components JSON structure on edges."""
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
            type=MetricType.BLOOD_GLUCOSE, value=160, unit="mg/dL",
            measured_at=datetime.now(timezone.utc), source="test",
        ),
    )
    
    components = ConfidenceComponents(
        pattern_strength=0.9,
        temporal_alignment=0.8,
        effect_magnitude=0.7,
        data_quality=0.9,
    )
    
    service = HealthGraphService(db)
    edge = await service.upsert_edge(
        user_id, HealthMetricEdgeCreate(
            source_metric_id=source.id,
            target_metric_id=target.id,
            edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
            confidence=components.combined_score(),
            algorithm="test.v1",
            evidence={"components": components.to_dict()},
            confidence_components=components.to_dict(),
        ),
    )
    
    assert edge.confidence_components is not None
    assert edge.confidence_components["pattern_strength"] == 0.9


@pytest.mark.asyncio
async def test_confidence_thresholds_language(db_session, test_user):
    """Test confidence thresholds map to language."""
    # Low confidence (< 0.6)
    assert categorize_confidence(0.5) == "low"
    # Medium confidence (0.6-0.8)
    assert categorize_confidence(0.7) == "medium"
    # High confidence (>= 0.8)
    assert categorize_confidence(0.9) == "high"


@pytest.mark.asyncio
async def test_confidence_overall_calculation(db_session, test_user):
    components = ConfidenceComponents(
        pattern_strength=0.8,
        temporal_alignment=0.7,
        effect_magnitude=0.6,
        data_quality=0.9,
    )
    
    expected = (0.8 * 0.4 + 0.7 * 0.3 + 0.6 * 0.2 + 0.9 * 0.1)
    assert abs(components.combined_score() - expected) < 0.01