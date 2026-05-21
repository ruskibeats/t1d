"""Tests for RAG evidence contract — graph context retrieval for LLM."""

import pytest
from datetime import datetime, timezone

from app.metrics.graph_service import HealthGraphService
from app.metrics.schemas import HealthMetricCreate, HealthMetricEdgeCreate
from app.metrics.types import GraphEdgeType, MetricType
from app.metrics.service import HealthMetricService


@pytest.mark.asyncio
async def test_graph_context_retrieval_for_llm(db_session, test_user):
    """Test that graph context is properly formatted for LLM retrieval."""
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

    service = HealthGraphService(db)
    edge = await service.upsert_edge(
        user_id, HealthMetricEdgeCreate(
            source_metric_id=source.id,
            target_metric_id=target.id,
            edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
            confidence=0.8,
            algorithm="pattern_service.post_meal_spike.v1",
            evidence={"post_meal_spike": True, "rise_amount": 50},
        ),
    )

    # Verify RAG context includes evidence
    assert edge.evidence is not None
    assert edge.evidence.get("post_meal_spike") is True


@pytest.mark.asyncio
async def test_strongest_edge_context(db_session, test_user):
    """Test that strongest edges provide meaningful context for LLM."""
    db = db_session
    user_id = test_user.id

    # Create multiple edges with different strengths
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
    for i in range(3):
        await service.upsert_edge(
            user_id, HealthMetricEdgeCreate(
                source_metric_id=source.id,
                target_metric_id=target.id,
                edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
                confidence=0.5 + i * 0.15,
                algorithm="test.v1",
                evidence={"iteration": i},
            ),
        )

    # Get strongest edges
    edges = await service.get_strongest_edges(user_id, None, 5)
    assert len(edges) >= 1
    assert all(e.confidence >= 0.5 for e in edges)