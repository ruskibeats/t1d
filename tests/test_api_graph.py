"""API tests for health graph endpoints."""

import pytest
from datetime import datetime, timedelta, timezone

from app.api.metrics import (
    create_graph_edge,
    get_health_subgraph,
    get_metric_causes,
    get_metric_effects,
    get_metric_neighbors,
    query_graph_edges,
)
from app.metrics.schemas import HealthMetricCreate, HealthMetricEdgeCreate
from app.metrics.service import HealthMetricService
from app.metrics.types import GraphEdgeType, MetricType


@pytest.mark.asyncio
async def test_graph_api_edge_lifecycle(db_session, test_user):
    metric_service = HealthMetricService(db_session)
    now = datetime.now(timezone.utc)
    source = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.CARBS, value=50, unit="g", measured_at=now, source="manual"),
    )
    target = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.BLOOD_GLUCOSE, value=210, unit="mg/dL", measured_at=now + timedelta(hours=2), source="dexcom"),
    )

    created = await create_graph_edge(
        data=HealthMetricEdgeCreate(
            source_metric_id=source.id,
            target_metric_id=target.id,
            edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
            confidence=0.7,
            time_delay_seconds=7200,
            algorithm="api-test",
        ),
        user=test_user,
        db=db_session,
    )
    assert created.edge_type == GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE

    edges = await query_graph_edges(
        user=test_user,
        edge_types=[GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE],
        min_confidence=0.6,
        source_metric_id=None,
        target_metric_id=None,
        limit=100,
        offset=0,
        db=db_session,
    )
    assert len(edges) == 1
    assert edges[0].id == created.id

    neighbors = await get_metric_neighbors(source.id, user=test_user, db=db_session)
    assert len(neighbors.outgoing) == 1
    assert neighbors.incoming == []

    causes = await get_metric_causes(target.id, user=test_user, limit=20, db=db_session)
    assert len(causes) == 1
    assert causes[0].source_metric_id == source.id

    effects = await get_metric_effects(source.id, user=test_user, limit=20, db=db_session)
    assert len(effects) == 1
    assert effects[0].target_metric_id == target.id

    subgraph = await get_health_subgraph(center_metric_id=source.id, user=test_user, depth=1, db=db_session)
    assert {node.id for node in subgraph.nodes} == {source.id, target.id}
    assert len(subgraph.edges) == 1
