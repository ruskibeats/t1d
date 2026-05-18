"""Tests for same_event_as linking based on event_group_id."""

import pytest
from datetime import datetime, timezone

from app.metrics.service import HealthMetricService
from app.metrics.graph_service import HealthGraphService
from app.metrics.schemas import HealthMetricCreate
from app.metrics.types import GraphEdgeType, MetricType


@pytest.mark.asyncio
async def test_link_event_group_creates_edges(db_session, test_user):
    metric_service = HealthMetricService(db_session)
    graph_service = HealthGraphService(db_session)

    event_group_id = "group-abc-123"
    now = datetime.now(timezone.utc)

    # Create three metrics sharing the same event_group_id
    m1 = await metric_service.create(
        test_user.id,
        HealthMetricCreate(
            type=MetricType.CARBS,
            value=30,
            unit="g",
            measured_at=now,
            source="manual",
            event_group_id=event_group_id,
        ),
    )
    m2 = await metric_service.create(
        test_user.id,
        HealthMetricCreate(
            type=MetricType.PROTEIN,
            value=20,
            unit="g",
            measured_at=now,
            source="manual",
            event_group_id=event_group_id,
        ),
    )
    m3 = await metric_service.create(
        test_user.id,
        HealthMetricCreate(
            type=MetricType.FAT,
            value=10,
            unit="g",
            measured_at=now,
            source="manual",
            event_group_id=event_group_id,
        ),
    )

    # Link event group
    edges = await graph_service.link_event_group(test_user.id, event_group_id)
    assert len(edges) == 3  # C(3,2) pairs
    for e in edges:
        assert e.edge_type == GraphEdgeType.SAME_EVENT_AS
        assert e.confidence == 1.0
        assert e.algorithm == "event_group_link"
        assert e.evidence == {"event_group_id": event_group_id}

    # Calling again should not duplicate edges (upsert)
    edges_again = await graph_service.link_event_group(test_user.id, event_group_id)
    assert len(edges_again) == 3
    # Verify DB only has 3 SAME_EVENT_AS edges for this user
    all_edges = await graph_service.query_edges(
        test_user.id,
        params=type('Params', (), {
            "edge_types": [GraphEdgeType.SAME_EVENT_AS],
            "min_confidence": None,
            "source_metric_id": None,
            "target_metric_id": None,
            "limit": 100,
            "offset": 0,
        })(),
    )
    assert len(all_edges) == 3
