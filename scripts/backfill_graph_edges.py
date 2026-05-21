"""Graph backfill script — rebuild historical graph edges from existing health_metrics."""

import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics.graph_service import HealthGraphService
from app.metrics.models import HealthMetric
from app.metrics.schemas import HealthMetricEdgeCreate
from app.metrics.types import GraphEdgeType, MetricType
from app.core.database import get_db


async def backfill_meal_spike_edges(db: AsyncSession, user_id: int = None, days: int = 90):
    """Backfill MEAL_TO_GLUCOSE_SPIKE edges for historical data."""
    service = HealthGraphService(db)
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Find all meals
    query = select(HealthMetric).where(
        HealthMetric.type == MetricType.CARBS,
        HealthMetric.timestamp >= cutoff,
    )
    if user_id:
        query = query.where(HealthMetric.user_id == user_id)
    
    result = await db.execute(query.order_by(HealthMetric.timestamp))
    meals = result.scalars().all()
    
    for meal in meals:
        # Check for spike within 2 hours
        window_end = meal.timestamp + timedelta(hours=2)
        
        spike_query = select(HealthMetric).where(
            HealthMetric.user_id == meal.user_id,
            HealthMetric.type == MetricType.BLOOD_GLUCOSE,
            HealthMetric.timestamp >= meal.timestamp,
            HealthMetric.timestamp <= window_end,
            HealthMetric.value > 180,
        )
        spike_result = await db.execute(spike_query)
        spikes = spike_result.scalars().all()
        
        for spike in spikes:
            await service.upsert_edge(
                meal.user_id, HealthMetricEdgeCreate(
                    source_metric_id=meal.id,
                    target_metric_id=spike.id,
                    edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
                    confidence=0.7,
                    time_delay_seconds=int((spike.timestamp - meal.timestamp).total_seconds()),
                    algorithm="backfill.meal_spike_v1",
                    evidence={"backfilled": True, "historical": True},
                ),
            )


async def backfill_all_user_events(db: AsyncSession, user_id: int):
    """Backfill SAME_EVENT_AS edges for all event groups."""
    service = HealthGraphService(db)
    
    # Find all event groups with multiple metrics
    query = select(HealthMetric.event_group_id).where(
        HealthMetric.user_id == user_id,
        HealthMetric.event_group_id.is_not(None),
    ).distinct()
    
    result = await db.execute(query)
    event_groups = [row[0] for row in result.fetchall() if row[0]]
    
    for eg_id in event_groups:
        await service.link_event_group(user_id, eg_id)


if __name__ == "__main__":
    async def main():
        async for db in get_db():
            await backfill_meal_spike_edges(db)
            break
    
    asyncio.run(main())