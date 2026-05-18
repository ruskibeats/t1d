"""Pydantic schemas for the metrics domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.metrics.types import GraphEdgeType, MetricType


class HealthMetricCreate(BaseModel):
    event_group_id: Optional[str] = None
    """Schema for creating a health metric entry."""

    type: MetricType = Field(..., description="Metric type identifier")
    value: float = Field(..., ge=0, description="Measured value")
    unit: str = Field(..., max_length=50, description="Unit of measurement")
    measured_at: datetime = Field(..., description="Timestamp of measurement (timezone-aware)")
    ended_at: Optional[datetime] = Field(None, description="End time for ranged metrics (sleep, exercise)")
    source: str = Field(..., max_length=50, description="Source system: dexcom, garmin, manual, apple_health, etc.")
    provider_id: Optional[str] = Field(None, max_length=255, description="External provider's unique ID for dedup")
    event_group_id: Optional[str] = Field(None, description="Identifier for grouping related metric events")
    meta: Optional[dict[str, Any]] = Field(None, description="Type-specific payload")


class HealthMetricResponse(BaseModel):
    event_group_id: Optional[str] = None
    """Schema for a health metric entry response."""

    id: int
    user_id: int
    type: MetricType
    value: float
    unit: str
    measured_at: datetime
    ended_at: Optional[datetime]
    source: str
    provider_id: Optional[str]
    event_group_id: Optional[str]
    meta: Optional[dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchHealthMetricCreate(BaseModel):
    """Schema for batch creating health metrics."""

    metrics: list[HealthMetricCreate] = Field(..., min_length=1, max_length=1000)
    source: Optional[str] = Field(None, description="Default source for all metrics (overridden per-metric)")


class HealthMetricQuery(BaseModel):
    """Schema for querying health metrics."""

    start_time: datetime
    end_time: datetime
    types: Optional[list[MetricType]] = Field(None, description="Filter by metric types")
    sources: Optional[list[str]] = Field(None, description="Filter by sources")
    limit: int = Field(100, ge=1, le=10000)
    offset: int = Field(0, ge=0)


class HealthMetricEdgeCreate(BaseModel):
    """Schema for creating a graph edge between two health metric nodes."""

    source_metric_id: int = Field(..., ge=1)
    target_metric_id: int = Field(..., ge=1)
    edge_type: GraphEdgeType
    confidence: float = Field(0.5, ge=0, le=1)
    time_delay_seconds: Optional[int] = Field(None, description="Delay from source metric to target metric")
    algorithm: str = Field("manual", max_length=100)
    evidence: Optional[dict[str, Any]] = Field(None, description="Explainability metadata for this relationship")


class HealthMetricEdgeResponse(BaseModel):
    """Schema for a graph edge response."""

    id: int
    user_id: int
    source_metric_id: int
    target_metric_id: int
    edge_type: GraphEdgeType
    confidence: float
    time_delay_seconds: Optional[int]
    algorithm: str
    evidence: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthMetricEdgeQuery(BaseModel):
    """Schema for querying graph edges."""

    edge_types: Optional[list[GraphEdgeType]] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    source_metric_id: Optional[int] = Field(None, ge=1)
    target_metric_id: Optional[int] = Field(None, ge=1)
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class GraphNeighborResponse(BaseModel):
    """Incoming and outgoing edges for a graph node."""

    metric_id: int
    incoming: list[HealthMetricEdgeResponse]
    outgoing: list[HealthMetricEdgeResponse]


class HealthSubgraphResponse(BaseModel):
    """Compact graph response with nodes and edges."""

    nodes: list[HealthMetricResponse]
    edges: list[HealthMetricEdgeResponse]


class DailyAggregateQuery(BaseModel):
    """Schema for querying daily aggregates."""

    start_date: datetime
    end_date: datetime
    types: Optional[list[MetricType]] = None


class HealthMetricSummary(BaseModel):
    """Summary statistics for a metric type over a time range."""

    type: MetricType
    count: int
    avg: Optional[float]
    min: Optional[float]
    max: Optional[float]
    sum: Optional[float]
    first: Optional[datetime]
    last: Optional[datetime]
