---
name: graph-backfill-script-creation
description: Procedure for creating a backfill script to rebuild historical graph edges from existing health_metrics data after schema changes or adding new edge types.
---

# Graph Backfill Script Creation

## When to Use
When you need to rebuild historical graph edges from existing health_metrics data after adding new edge types or changing the graph schema.

## Procedure

### 1. Create the script file
Create `scripts/backfill_graph_edges.py` with the following structure:

```python
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
```

### 2. Implement backfill functions
- `backfill_meal_spike_edges(db, user_id=None, days=90)` - Rebuild MEAL_TO_GLUCOSE_SPIKE edges
- `backfill_all_user_events(db, user_id)` - Rebuild SAME_EVENT_AS edges for event groups
- Use `HealthGraphService.upsert_edge()` to avoid duplicates
- Include `evidence={"backfilled": True, "historical": True}`
- Set appropriate confidence scores (typically 0.7 for backfilled data)

### 3. Add main execution
```python
if __name__ == "__main__":
    async def main():
        async for db in get_db():
            await backfill_meal_spike_edges(db)
            break

    asyncio.run(main())
```

### 4. Test the script
- Run with a limited time window first (days=7)
- Verify edge counts match expectations
- Check for duplicate edges (upsert should handle this)

## Pitfalls
- Don't backfill indefinitely — set a reasonable days limit (default 90)
- Use `upsert_edge` not `create_edge` to avoid duplicates
- Include `algorithm` and `evidence` fields for provenance tracking
- Test with a single user first before running for all users

## Verification
- Script runs without errors
- Edge counts match expected historical data
- No duplicate edges created
- Backfilled edges have proper provenance fields
