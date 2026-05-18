"""SQLAlchemy models for the unified health metric store."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.metrics.types import GraphEdgeType, MetricType

metric_type_enum = ENUM(
    *[t.value for t in MetricType],
    name="metric_type",
    create_type=True,
    metadata=Base.metadata,
)

graph_edge_type_enum = ENUM(
    *[t.value for t in GraphEdgeType],
    name="graph_edge_type",
    create_type=True,
    metadata=Base.metadata,
)


class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("tbl_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[MetricType] = mapped_column(metric_type_enum, nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_group_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="health_metrics")

    __table_args__ = (
        Index("ix_health_metrics_user_type_time", "user_id", "type", "measured_at"),
        Index("ix_health_metrics_user_time", "user_id", "measured_at"),
        Index("ix_health_metrics_dedup", "user_id", "type", "source", "provider_id",
              unique=True, postgresql_where="provider_id IS NOT NULL"),
        CheckConstraint("value >= 0", name="ck_health_metrics_value_positive"),
    )

    def __repr__(self) -> str:
        return f"<HealthMetric {self.type}={self.value} {self.unit} @ {self.measured_at}>"


class HealthMetricEdge(Base):
    """Directed relationship between two HealthMetric nodes.

    Edges turn the unified metrics feed into a graph. They are evidence records
    created by pattern detection or ingestion logic, e.g. a meal metric followed
    by a glucose spike metric with a confidence and time delay.
    """

    __tablename__ = "health_metric_edges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_metric_id: Mapped[int] = mapped_column(ForeignKey("health_metrics.id", ondelete="CASCADE"), nullable=False)
    target_metric_id: Mapped[int] = mapped_column(ForeignKey("health_metrics.id", ondelete="CASCADE"), nullable=False)
    edge_type: Mapped[GraphEdgeType] = mapped_column(graph_edge_type_enum, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    time_delay_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")
    evidence: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_health_edges_user_source", "user_id", "source_metric_id"),
        Index("ix_health_edges_user_target", "user_id", "target_metric_id"),
        Index("ix_health_edges_user_type", "user_id", "edge_type"),
        Index("ix_health_edges_user_type_conf", "user_id", "edge_type", "confidence"),
        UniqueConstraint("source_metric_id", "target_metric_id", "edge_type", name="uq_health_edges_source_target_type"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_health_edges_confidence_range"),
        CheckConstraint("source_metric_id <> target_metric_id", name="ck_health_edges_not_self"),
    )

    def __repr__(self) -> str:
        return f"<HealthMetricEdge {self.edge_type} {self.source_metric_id}->{self.target_metric_id} conf={self.confidence}>"


class HealthDailyAggregate(Base):
    __tablename__ = "health_daily_aggregates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[MetricType] = mapped_column(metric_type_enum, nullable=False)
    local_date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    value_sum: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_last: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_primary: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True,
    )
    aggregation_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="health_daily_aggregates")

    __table_args__ = (
        UniqueConstraint("user_id", "type", "local_date", name="uq_aggregates_user_type_date"),
        Index("ix_aggregates_user_date", "user_id", "local_date"),
        Index("ix_aggregates_user_type_date", "user_id", "type", "local_date"),
    )

    def __repr__(self) -> str:
        return f"<HealthDailyAggregate {self.type} [{self.local_date}] avg={self.value_avg}>"
