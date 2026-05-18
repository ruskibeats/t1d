"""Tests for the central health metrics graph layer."""

import pytest
from datetime import datetime, timedelta, timezone

from app.metrics.graph_service import HealthGraphService
from app.metrics.schemas import HealthMetricCreate, HealthMetricEdgeCreate, HealthMetricEdgeQuery
from app.metrics.service import HealthMetricService
from app.metrics.types import GraphEdgeType, MetricType


@pytest.mark.asyncio
async def test_create_and_query_graph_edge(db_session, test_user):
    metric_service = HealthMetricService(db_session)
    now = datetime.now(timezone.utc)
    carbs = await metric_service.create(
        test_user.id,
        HealthMetricCreate(
            type=MetricType.CARBS,
            value=60,
            unit="g",
            measured_at=now,
            source="manual",
        ),
    )
    glucose = await metric_service.create(
        test_user.id,
        HealthMetricCreate(
            type=MetricType.BLOOD_GLUCOSE,
            value=220,
            unit="mg/dL",
            measured_at=now + timedelta(hours=2),
            source="dexcom",
        ),
    )

    graph = HealthGraphService(db_session)
    edge = await graph.create_edge(
        test_user.id,
        HealthMetricEdgeCreate(
            source_metric_id=carbs.id,
            target_metric_id=glucose.id,
            edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
            confidence=0.82,
            time_delay_seconds=7200,
            algorithm="test",
            evidence={"rise_mg_dl": 90},
        ),
    )

    assert edge.id is not None
    assert edge.confidence == 0.82
    assert edge.evidence["rise_mg_dl"] == 90

    queried = await graph.query_edges(
        test_user.id,
        HealthMetricEdgeQuery(edge_types=[GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE]),
    )
    assert len(queried) == 1
    assert queried[0].source_metric_id == carbs.id


@pytest.mark.asyncio
async def test_upsert_edge_deduplicates_and_keeps_stronger_confidence(db_session, test_user):
    metric_service = HealthMetricService(db_session)
    now = datetime.now(timezone.utc)
    source = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.EXERCISE_MINUTES, value=45, unit="minutes", measured_at=now, source="manual"),
    )
    target = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.BLOOD_GLUCOSE, value=65, unit="mg/dL", measured_at=now + timedelta(hours=1), source="dexcom"),
    )
    graph = HealthGraphService(db_session)

    first = await graph.upsert_edge(
        test_user.id,
        HealthMetricEdgeCreate(
            source_metric_id=source.id,
            target_metric_id=target.id,
            edge_type=GraphEdgeType.EXERCISE_TO_GLUCOSE_DROP,
            confidence=0.55,
            evidence={"drop_mg_dl": 45},
        ),
    )
    second = await graph.upsert_edge(
        test_user.id,
        HealthMetricEdgeCreate(
            source_metric_id=source.id,
            target_metric_id=target.id,
            edge_type=GraphEdgeType.EXERCISE_TO_GLUCOSE_DROP,
            confidence=0.75,
            evidence={"sessions": 3},
        ),
    )

    assert first.id == second.id
    assert second.confidence == 0.75
    assert second.evidence["drop_mg_dl"] == 45
    assert second.evidence["sessions"] == 3

    edges = await graph.query_edges(test_user.id, HealthMetricEdgeQuery())
    assert len(edges) == 1


@pytest.mark.asyncio
async def test_neighbors_causes_effects_and_subgraph(db_session, test_user):
    metric_service = HealthMetricService(db_session)
    graph = HealthGraphService(db_session)
    now = datetime.now(timezone.utc)
    meal = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.CARBS, value=80, unit="g", measured_at=now, source="manual"),
    )
    insulin = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.INSULIN_BOLUS, value=7, unit="units", measured_at=now, source="manual"),
    )
    glucose = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.BLOOD_GLUCOSE, value=240, unit="mg/dL", measured_at=now + timedelta(hours=3), source="dexcom"),
    )

    await graph.create_edge(
        test_user.id,
        HealthMetricEdgeCreate(source_metric_id=meal.id, target_metric_id=glucose.id, edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE, confidence=0.8),
    )
    await graph.create_edge(
        test_user.id,
        HealthMetricEdgeCreate(source_metric_id=insulin.id, target_metric_id=glucose.id, edge_type=GraphEdgeType.INSULIN_TO_GLUCOSE_CHANGE, confidence=0.6),
    )

    incoming, outgoing = await graph.get_neighbors(test_user.id, glucose.id)
    assert len(incoming) == 2
    assert outgoing == []

    causes = await graph.get_causes(test_user.id, glucose.id)
    assert [edge.confidence for edge in causes] == [0.8, 0.6]

    effects = await graph.get_effects(test_user.id, meal.id)
    assert len(effects) == 1
    assert effects[0].target_metric_id == glucose.id

    nodes, edges = await graph.get_subgraph(test_user.id, glucose.id, depth=1)
    assert {node.id for node in nodes} == {meal.id, insulin.id, glucose.id}
    assert len(edges) == 2


@pytest.mark.asyncio
async def test_graph_service_rejects_cross_user_edges(db_session, test_user, test_user_2):
    metric_service = HealthMetricService(db_session)
    now = datetime.now(timezone.utc)
    source = await metric_service.create(
        test_user.id,
        HealthMetricCreate(type=MetricType.CARBS, value=40, unit="g", measured_at=now, source="manual"),
    )
    target = await metric_service.create(
        test_user_2.id,
        HealthMetricCreate(type=MetricType.BLOOD_GLUCOSE, value=200, unit="mg/dL", measured_at=now, source="dexcom"),
    )

    graph = HealthGraphService(db_session)
    with pytest.raises(ValueError):
        await graph.create_edge(
            test_user.id,
            HealthMetricEdgeCreate(
                source_metric_id=source.id,
                target_metric_id=target.id,
                edge_type=GraphEdgeType.CORRELATES_WITH,
            ),
        )
