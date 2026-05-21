---
name: graph-backfill-script
description: Script to rebuild historical graph edges from existing health_metrics data when deploying new edge types or changing the graph schema.
---

# Graph Backfill Script

## Purpose
Create a script to rebuild historical graph edges from existing health_metrics data.

## When to Use
When deploying graph edge persistence to production and needing to backfill historical data.

## Procedure

### 1. Create backfill script
```python
# scripts/backfill_graph_edges.py
import asyncio
from datetime import datetime, timezone
from app.core.database import get_db
from app.metrics.graph_service import HealthGraphService
from app.metrics.service import HealthMetricService
from app.metrics.types import GraphEdgeType, MetricType

async def backfill_user_graph(user_id: int, days: int = 90):
    """Rebuild graph edges for a user from historical metrics."""
    db = await get_db()
    metric_service = HealthMetricService(db)
    graph_service = HealthGraphService(db)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all metrics for user
    metrics = await metric_service.get_metrics(user_id, since=cutoff)

    # Group by type for pattern detection
    meals = [m for m in metrics if m.type == MetricType.CARBS]
    glucose = [m for m in metrics if m.type == MetricType.BLOOD_GLUCOSE]
    exercise = [m for m in metrics if m.type == MetricType.EXERCISE_MINUTES]

    edges_created = 0

    # Backfill meal-to-glucose spikes
    for meal in meals:
        # Find nearest glucose after meal
        target = find_nearest(glucose, meal.measured_at, hours=3)
        if target and target.value > meal.value + 50:
            edge = await graph_service.upsert_edge(
                user_id,
                HealthMetricEdgeCreate(
                    source_metric_id=meal.id,
                    target_metric_id=target.id,
                    edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
                    confidence=min((target.value - meal.value) / 100, 1.0),
                    algorithm="backfill.post_meal_spike.v1",
                    evidence={"carbs": meal.value, "rise": target.value - meal.value},
                ),
            )
            edges_created += 1

    print(f"Created {edges_created} edges for user {user_id}")
    return edges_created

if __name__ == "__main__":
    import sys
    user_id = int(sys.argv[1])
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    asyncio.run(backfill_user_graph(user_id, days))
```

### 2. Run backfill
```bash
python scripts/backfill_graph_edges.py <user_id> <days>
```

### 3. Report counts by edge type
```python
edge_counts = {
    "meal_to_glucose_spike": 0,
    "exercise_to_glucose_drop": 0,
    "sleep_to_next_day_glucose": 0,
}

for edge in edges:
    edge_counts[edge.edge_type] += 1

print(f"Edge counts: {edge_counts}")
```

## Verification
- Script can rebuild entire graph from existing data
- Edge counts match expected patterns
- No duplicate edges created
- Handles upserts properly

## Related Files
- `scripts/backfill_graph_edges.py`
- `app/metrics/graph_service.py`
- `app/services/pattern_service.py`
