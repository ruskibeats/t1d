"""FastAPI routes for unified health metrics ingestion and querying."""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.metrics.schemas import (
    BatchHealthMetricCreate,
    HealthMetricCreate,
    HealthMetricQuery,
    GraphNeighborResponse,
    HealthMetricEdgeCreate,
    HealthMetricEdgeQuery,
    HealthMetricEdgeResponse,
    HealthMetricResponse,
    HealthMetricSummary,
    HealthSubgraphResponse,
)
from app.metrics.graph_service import HealthGraphService
from app.metrics.service import HealthMetricService, HealthAggregateService
from app.metrics.types import GraphEdgeType, MetricType

logger = get_logger(__name__)
route = APIRouter(prefix="/metrics", tags=["metrics"])


@route.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=HealthMetricResponse,
    summary="Create a single health metric",
    description="Unified endpoint for all health data ingestion. Accepts one metric entry.",
)
async def create_metric(
    data: HealthMetricCreate,
    user_id: int = Query(..., description="User ID (placeholder — replace with auth)", ge=1),
    db: AsyncSession = Depends(get_db),
) -> HealthMetricResponse:
    service = HealthMetricService(db)
    metric = await service.create(user_id, data)
    return HealthMetricResponse.model_validate(metric)


@route.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    response_model=dict[str, Any],
    summary="Batch create health metrics",
    description="Create multiple health metrics at once. Useful for bulk device sync.",
)
async def create_metrics_batch(
    data: BatchHealthMetricCreate,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    service = HealthMetricService(db)
    created, skipped = await service.create_batch(user_id, data)
    return {
        "created": len(created),
        "skipped": skipped,
        "metrics": [HealthMetricResponse.model_validate(m).model_dump() for m in created],
    }


@route.get(
    "",
    response_model=list[HealthMetricResponse],
    summary="Query health metrics",
    description="Query metrics by time range, type, and source.",
)
async def query_metrics(
    user_id: int = Query(..., ge=1),
    start: datetime = Query(..., description="Start time (ISO 8601, timezone-aware)"),
    end: datetime = Query(..., description="End time (ISO 8601, timezone-aware)"),
    types: list[MetricType] = Query(default=[], description="Filter by metric types"),
    sources: list[str] = Query(default=[], description="Filter by sources"),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[HealthMetricResponse]:
    service = HealthMetricService(db)
    params = HealthMetricQuery(
        start_time=start,
        end_time=end,
        types=types if types else None,
        sources=sources if sources else None,
        limit=limit,
        offset=offset,
    )
    metrics = await service.query(user_id, params)
    return [HealthMetricResponse.model_validate(m) for m in metrics]


@route.get(
    "/summary",
    response_model=HealthMetricSummary,
    summary="Get metric summary for a time range",
)
async def get_summary(
    user_id: int = Query(..., ge=1),
    metric_type: MetricType = Query(..., description="Metric type to summarize"),
    hours: int = Query(24, ge=1, le=720),  # 1h to 30 days
    db: AsyncSession = Depends(get_db),
) -> HealthMetricSummary:
    service = HealthMetricService(db)
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    return await service.get_summary(user_id, metric_type, start, end)


@route.get(
    "/recent",
    response_model=dict[str, list[HealthMetricResponse]],
    summary="Get recent metrics by type",
    description="Returns the most recent metrics per type within the last N hours.",
)
async def get_recent(
    user_id: int = Query(..., ge=1),
    types: list[MetricType] = Query(default=[MetricType.BLOOD_GLUCOSE], description="Metric types to retrieve"),
    hours: int = Query(24, ge=1, le=72),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[HealthMetricResponse]]:
    service = HealthMetricService(db)
    results = await service.get_recent(user_id, types, hours)
    return {
        t.value: [HealthMetricResponse.model_validate(m) for m in metrics]
        for t, metrics in results.items()
    }


@route.delete(
    "/{metric_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a metric",
)
async def delete_metric(
    metric_id: int,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    service = HealthMetricService(db)
    deleted = await service.delete(user_id, metric_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Metric not found")


# ---------------------------------------------------------------------------
# Health graph endpoints
# ---------------------------------------------------------------------------


@route.post(
    "/graph/edges",
    status_code=status.HTTP_201_CREATED,
    response_model=HealthMetricEdgeResponse,
    summary="Create a graph edge between health metrics",
)
async def create_graph_edge(
    data: HealthMetricEdgeCreate,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> HealthMetricEdgeResponse:
    service = HealthGraphService(db)
    try:
        edge = await service.upsert_edge(user_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return HealthMetricEdgeResponse.model_validate(edge)


@route.get(
    "/graph/edges",
    response_model=list[HealthMetricEdgeResponse],
    summary="Query graph edges",
)
async def query_graph_edges(
    user_id: int = Query(..., ge=1),
    edge_types: list[GraphEdgeType] = Query(default=[]),
    min_confidence: float | None = Query(None, ge=0, le=1),
    source_metric_id: int | None = Query(None, ge=1),
    target_metric_id: int | None = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[HealthMetricEdgeResponse]:
    service = HealthGraphService(db)
    params = HealthMetricEdgeQuery(
        edge_types=edge_types or None,
        min_confidence=min_confidence,
        source_metric_id=source_metric_id,
        target_metric_id=target_metric_id,
        limit=limit,
        offset=offset,
    )
    edges = await service.query_edges(user_id, params)
    return [HealthMetricEdgeResponse.model_validate(e) for e in edges]


@route.get(
    "/graph/metrics/{metric_id}/neighbors",
    response_model=GraphNeighborResponse,
    summary="Get graph neighbors for a metric",
)
async def get_metric_neighbors(
    metric_id: int,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> GraphNeighborResponse:
    service = HealthGraphService(db)
    try:
        incoming, outgoing = await service.get_neighbors(user_id, metric_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return GraphNeighborResponse(
        metric_id=metric_id,
        incoming=[HealthMetricEdgeResponse.model_validate(e) for e in incoming],
        outgoing=[HealthMetricEdgeResponse.model_validate(e) for e in outgoing],
    )


@route.get(
    "/graph/metrics/{metric_id}/causes",
    response_model=list[HealthMetricEdgeResponse],
    summary="Get likely causes leading into a metric",
)
async def get_metric_causes(
    metric_id: int,
    user_id: int = Query(..., ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[HealthMetricEdgeResponse]:
    service = HealthGraphService(db)
    try:
        edges = await service.get_causes(user_id, metric_id, limit)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return [HealthMetricEdgeResponse.model_validate(e) for e in edges]


@route.get(
    "/graph/metrics/{metric_id}/effects",
    response_model=list[HealthMetricEdgeResponse],
    summary="Get likely effects following a metric",
)
async def get_metric_effects(
    metric_id: int,
    user_id: int = Query(..., ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[HealthMetricEdgeResponse]:
    service = HealthGraphService(db)
    try:
        edges = await service.get_effects(user_id, metric_id, limit)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return [HealthMetricEdgeResponse.model_validate(e) for e in edges]


@route.get(
    "/graph/subgraph",
    response_model=HealthSubgraphResponse,
    summary="Get a small subgraph around a metric",
)
async def get_health_subgraph(
    center_metric_id: int = Query(..., ge=1),
    user_id: int = Query(..., ge=1),
    depth: int = Query(1, ge=0, le=3),
    db: AsyncSession = Depends(get_db),
) -> HealthSubgraphResponse:
    service = HealthGraphService(db)
    try:
        nodes, edges = await service.get_subgraph(user_id, center_metric_id, depth)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return HealthSubgraphResponse(
        nodes=[HealthMetricResponse.model_validate(n) for n in nodes],
        edges=[HealthMetricEdgeResponse.model_validate(e) for e in edges],
    )


@route.get(
    "/graph/recent-correlations",
    response_model=list[HealthMetricEdgeResponse],
    summary="Get strongest recent graph relationships",
)
async def get_recent_graph_correlations(
    user_id: int = Query(..., ge=1),
    edge_types: list[GraphEdgeType] = Query(default=[]),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[HealthMetricEdgeResponse]:
    service = HealthGraphService(db)
    edges = await service.get_strongest_edges(user_id, edge_types or None, limit)
    return [HealthMetricEdgeResponse.model_validate(e) for e in edges]
