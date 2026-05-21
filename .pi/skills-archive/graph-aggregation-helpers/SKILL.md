---
name: graph-aggregation-helpers
description: Reusable aggregation query patterns for the health metrics graph: edge counts by type, average confidence, strongest recurring pairs, and edge statistics.
---

# Graph Aggregation Helpers

## When to Use
When adding dashboard statistics or summary queries to the graph service, implement aggregation helper methods.

## Procedure

### 1. Add to HealthGraphService
```python
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
```

### 2. Add edge count by type
```python
async def edge_count_by_type(self, user_id: int, days: int = 14) -> dict:
    """Count edges by type for recent period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    # Group by edge_type, count
```

### 3. Add average confidence by type
```python
async def avg_confidence_by_type(self, user_id: int) -> dict:
    """Average confidence per edge type."""
    # Group by edge_type, avg confidence
```

### 4. Add strongest recurring pairs
```python
async def strongest_recurring_pairs(self, user_id: int, limit: int = 20) -> list:
    """Get most confident recurring edge pairs."""
    # Order by confidence, limit
```

## Pitfalls
- Use `self.db.func` for database functions (count, avg)
- Handle null results with `or 0` / `or ""`
- Round floating point results for display
- Test with empty result sets

## Verification
- Statistics match manual counts
- Average calculations are correct
- Limit parameters work correctly
- Empty result sets handled gracefully
