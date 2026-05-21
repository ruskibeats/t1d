"""Graph service for health metric relationship edges."""

from __future__ import annotations

from collections import deque

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics.models import HealthMetric, HealthMetricEdge
from app.metrics.schemas import HealthMetricEdgeCreate, HealthMetricEdgeQuery
from app.metrics.types import GraphEdgeType


class HealthGraphService:
    """Service for the health metrics graph.

    The graph is user-scoped. Nodes are rows in ``health_metrics`` and edges are
    rows in ``health_metric_edges``. Edges are observational evidence only.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_edge(self, user_id: int, data: HealthMetricEdgeCreate) -> HealthMetricEdge:
        """Create a directed edge after verifying both nodes belong to user."""
        await self._assert_metric_ownership(user_id, data.source_metric_id)
        await self._assert_metric_ownership(user_id, data.target_metric_id)
        edge = HealthMetricEdge(
            user_id=user_id,
            source_metric_id=data.source_metric_id,
            target_metric_id=data.target_metric_id,
            edge_type=data.edge_type,
            confidence=data.confidence,
            time_delay_seconds=data.time_delay_seconds,
            algorithm=data.algorithm,
            evidence=data.evidence,
            provenance=data.provenance,
            confidence_components=data.confidence_components,
        )
        self.db.add(edge)
        await self.db.flush()
        await self.db.refresh(edge)
        return edge

    async def upsert_edge(self, user_id: int, data: HealthMetricEdgeCreate) -> HealthMetricEdge:
        """Create or update an edge unique by source, target, edge type."""
        await self._assert_metric_ownership(user_id, data.source_metric_id)
        await self._assert_metric_ownership(user_id, data.target_metric_id)
        result = await self.db.execute(
            select(HealthMetricEdge).where(
                HealthMetricEdge.user_id == user_id,
                HealthMetricEdge.source_metric_id == data.source_metric_id,
                HealthMetricEdge.target_metric_id == data.target_metric_id,
                HealthMetricEdge.edge_type == data.edge_type,
            )
        )
        edge = result.scalar_one_or_none()
        if edge:
            edge.confidence = max(edge.confidence, data.confidence)
            edge.time_delay_seconds = data.time_delay_seconds
            edge.algorithm = data.algorithm
            edge.evidence = {**(edge.evidence or {}), **(data.evidence or {})}
            if data.provenance:
                edge.provenance = data.provenance
            if data.confidence_components:
                edge.confidence_components = data.confidence_components
            await self.db.flush()
            await self.db.refresh(edge)
            return edge
        return await self.create_edge(user_id, data)

    async def query_edges(self, user_id: int, params: HealthMetricEdgeQuery) -> list[HealthMetricEdge]:
        stmt = select(HealthMetricEdge).where(HealthMetricEdge.user_id == user_id)
        if params.edge_types:
            stmt = stmt.where(HealthMetricEdge.edge_type.in_(params.edge_types))
        if params.min_confidence is not None:
            stmt = stmt.where(HealthMetricEdge.confidence >= params.min_confidence)
        if params.source_metric_id is not None:
            stmt = stmt.where(HealthMetricEdge.source_metric_id == params.source_metric_id)
        if params.target_metric_id is not None:
            stmt = stmt.where(HealthMetricEdge.target_metric_id == params.target_metric_id)
        result = await self.db.execute(
            stmt.order_by(desc(HealthMetricEdge.confidence), desc(HealthMetricEdge.created_at))
            .offset(params.offset)
            .limit(params.limit)
        )
        return list(result.scalars().all())

    async def get_neighbors(self, user_id: int, metric_id: int) -> tuple[list[HealthMetricEdge], list[HealthMetricEdge]]:
        await self._assert_metric_ownership(user_id, metric_id)
        incoming_result = await self.db.execute(
            select(HealthMetricEdge)
            .where(HealthMetricEdge.user_id == user_id, HealthMetricEdge.target_metric_id == metric_id)
            .order_by(desc(HealthMetricEdge.confidence))
        )
        outgoing_result = await self.db.execute(
            select(HealthMetricEdge)
            .where(HealthMetricEdge.user_id == user_id, HealthMetricEdge.source_metric_id == metric_id)
            .order_by(desc(HealthMetricEdge.confidence))
        )
        return list(incoming_result.scalars().all()), list(outgoing_result.scalars().all())

    async def get_causes(self, user_id: int, metric_id: int, limit: int = 20) -> list[HealthMetricEdge]:
        await self._assert_metric_ownership(user_id, metric_id)
        result = await self.db.execute(
            select(HealthMetricEdge)
            .where(HealthMetricEdge.user_id == user_id, HealthMetricEdge.target_metric_id == metric_id)
            .order_by(desc(HealthMetricEdge.confidence))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_effects(self, user_id: int, metric_id: int, limit: int = 20) -> list[HealthMetricEdge]:
        await self._assert_metric_ownership(user_id, metric_id)
        result = await self.db.execute(
            select(HealthMetricEdge)
            .where(HealthMetricEdge.user_id == user_id, HealthMetricEdge.source_metric_id == metric_id)
            .order_by(desc(HealthMetricEdge.confidence))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_strongest_edges(
        self,
        user_id: int,
        edge_types: list[GraphEdgeType] | None = None,
        limit: int = 20,
    ) -> list[HealthMetricEdge]:
        stmt = select(HealthMetricEdge).where(HealthMetricEdge.user_id == user_id)
        if edge_types:
            stmt = stmt.where(HealthMetricEdge.edge_type.in_(edge_types))
        result = await self.db.execute(
            stmt.order_by(desc(HealthMetricEdge.confidence), desc(HealthMetricEdge.created_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def get_subgraph(self, user_id: int, center_metric_id: int, depth: int = 1) -> tuple[list[HealthMetric], list[HealthMetricEdge]]:
        """Return a small breadth-first subgraph around a metric."""
        await self._assert_metric_ownership(user_id, center_metric_id)
        depth = max(0, min(depth, 3))
        seen_metrics = {center_metric_id}
        seen_edges: dict[int, HealthMetricEdge] = {}
        queue: deque[tuple[int, int]] = deque([(center_metric_id, 0)])

        while queue:
            metric_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            incoming, outgoing = await self.get_neighbors(user_id, metric_id)
            for edge in incoming + outgoing:
                seen_edges[edge.id] = edge
                other = edge.source_metric_id if edge.target_metric_id == metric_id else edge.target_metric_id
                if other not in seen_metrics:
                    seen_metrics.add(other)
                    queue.append((other, current_depth + 1))

        metric_result = await self.db.execute(
            select(HealthMetric).where(HealthMetric.user_id == user_id, HealthMetric.id.in_(seen_metrics))
        )
        return list(metric_result.scalars().all()), list(seen_edges.values())

    async def link_event_group(self, user_id: int, event_group_id: str) -> list[HealthMetricEdge]:
        """Create SAME_EVENT_AS edges between all metrics sharing the given event_group_id.

        Returns the list of edges that were created or updated.
        """
        # Fetch metric IDs for the event group
        result = await self.db.execute(
            select(HealthMetric.id).where(
                HealthMetric.user_id == user_id,
                HealthMetric.event_group_id == event_group_id,
            )
        )
        metric_ids = [row[0] for row in result.fetchall()]
        if len(metric_ids) < 2:
            return []
        # Ensure deterministic order
        metric_ids.sort()
        edges: list[HealthMetricEdge] = []
        # Create an edge for each unordered pair (source < target)
        from itertools import combinations
        for src_id, tgt_id in combinations(metric_ids, 2):
            edge_data = HealthMetricEdgeCreate(
                source_metric_id=src_id,
                target_metric_id=tgt_id,
                edge_type=GraphEdgeType.SAME_EVENT_AS,
                confidence=1.0,
                algorithm="event_group_link",
                evidence={"event_group_id": event_group_id},
            )
            edge = await self.upsert_edge(user_id, edge_data)
            edges.append(edge)
        return edges

    async def get_event_group(self, user_id: int, event_group_id: str) -> list[HealthMetric]:
        """Get all metrics belonging to an event group."""
        result = await self.db.execute(
            select(HealthMetric)
            .where(HealthMetric.user_id == user_id, HealthMetric.event_group_id == event_group_id)
            .order_by(HealthMetric.timestamp)
        )
        return list(result.scalars().all())

    async def get_edges_for_metric(
        self, user_id: int, metric_id: int, limit: int = 50
    ) -> tuple[list[HealthMetricEdge], list[HealthMetricEdge]]:
        """Get all edges involving a metric (incoming + outgoing)."""
        return await self.get_neighbors(user_id, metric_id)

    async def get_recent_correlations(
        self, user_id: int, hours: int = 24, limit: int = 20
    ) -> list[HealthMetricEdge]:
        """Get recently created edge correlations."""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.db.execute(
            select(HealthMetricEdge)
            .where(HealthMetricEdge.user_id == user_id, HealthMetricEdge.created_at >= cutoff)
            .order_by(desc(HealthMetricEdge.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_edge_statistics(self, user_id: int) -> dict:
        """Get aggregate statistics for graph edges."""
        result = await self.db.execute(
            select(
                self.db.func.count(HealthMetricEdge.id).label("total_edges"),
                self.db.func.avg(HealthMetricEdge.confidence).label("avg_confidence"),
            ).where(HealthMetricEdge.user_id == user_id)
        )
        row = result.first()
        return {
            "total_edges": row.total_edges or 0,
            "avg_confidence": round(row.avg_confidence or 0, 3),
        }

    async def _assert_metric_ownership(self, user_id: int, metric_id: int) -> HealthMetric:
        result = await self.db.execute(
            select(HealthMetric).where(HealthMetric.user_id == user_id, HealthMetric.id == metric_id)
        )
        metric = result.scalar_one_or_none()
        if not metric:
            raise ValueError(f"Metric {metric_id} not found for user {user_id}")
        return metric