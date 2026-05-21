---
name: graph-service-patterns
description: Reusable patterns for HealthGraphService including subgraph traversal, neighbor queries, event group linking, and edge statistics.
---

# Graph Service Patterns

## Purpose
Reusable patterns for the HealthGraphService including subgraph traversal, neighbor queries, event group linking, and edge statistics.

## When to Use
When working with the health metrics graph - querying edges, traversing subgraphs, linking event groups, or getting statistics.

## Core Service Methods

### 1. Create and Upsert Edges
```python
# Create edge (fails if duplicate)
edge = await HealthGraphService(db).create_edge(
    user_id,
    HealthMetricEdgeCreate(...)
)

# Upsert edge (updates if exists)
edge = await HealthGraphService(db).upsert_edge(
    user_id,
    HealthMetricEdgeCreate(...)
)
```

### 2. Query Edges
```python
# Query with filters
edges = await HealthGraphService(db).query_edges(
    user_id,
    HealthMetricEdgeQuery(
        edge_types=[GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE],
        min_confidence=0.7,
        limit=20,
    )
)
```

### 3. Get Neighbors (Incoming/Outgoing)
```python
# Get all edges connected to a metric
incoming, outgoing = await HealthGraphService(db).get_neighbors(user_id, metric_id)
```

### 4. Get Causes and Effects
```python
# Get what caused a metric (incoming edges)
causes = await HealthGraphService(db).get_causes(user_id, metric_id, limit=20)

# Get what a metric caused (outgoing edges)
effects = await HealthGraphService(db).get_effects(user_id, metric_id, limit=20)
```

### 5. Get Strongest Edges
```python
strongest = await HealthGraphService(db).get_strongest_edges(
    user_id,
    edge_types=[GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE],
    limit=20
)
```

### 6. Subgraph Traversal
```python
# Get breadth-first subgraph around a metric
nodes, edges = await HealthGraphService(db).get_subgraph(
    user_id, center_metric_id, depth=1
)
```

### 7. Event Group Linking
```python
# Create SAME_EVENT_AS edges for all metrics in an event group
edges = await HealthGraphService(db).link_event_group(
    user_id, event_group_id
)

# Get all metrics in an event group
metrics = await HealthGraphService(db).get_event_group(
    user_id, event_group_id
)
```

### 8. Edge Statistics
```python
stats = await HealthGraphService(db).get_edge_statistics(user_id)
# Returns: {"total_edges": 150, "avg_confidence": 0.73}

recent = await HealthGraphService(db).get_recent_correlations(
    user_id, hours=24, limit=20
)
```

### 9. Get Edges for Metric
```python
incoming, outgoing = await HealthGraphService(db).get_edges_for_metric(
    user_id, metric_id, limit=50
)
```

## Key Patterns

### Subgraph Traversal (BFS)
```python
async def get_subgraph(self, user_id: int, center_metric_id: int, depth: int = 1):
    """Breadth-first traversal up to specified depth."""
    seen_metrics = {center_metric_id}
    seen_edges = {}
    queue = deque([(center_metric_id, 0)])
    
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
    
    # Fetch full metric objects
    result = await self.db.execute(
        select(HealthMetric).where(HealthMetric.user_id == user_id, HealthMetric.id.in_(seen_metrics))
    )
    return list(result.scalars().all()), list(seen_edges.values())
```

### Event Group Edge Creation
Uses itertools.combinations to create pairwise edges:
```python
from itertools import combinations
metric_ids = [m.id for m in metrics]  # sorted
for src_id, tgt_id in combinations(metric_ids, 2):
    edge = await self.upsert_edge(user_id, HealthMetricEdgeCreate(...))
```

### Neighbor Queries
```python
# Incoming edges (what caused this)
result = await self.db.execute(
    select(HealthMetricEdge)
    .where(HealthMetricEdge.user_id == user_id, HealthMetricEdge.target_metric_id == metric_id)
    .order_by(desc(HealthMetricEdge.confidence))
)

# Outgoing edges (what this caused)
result = await self.db.execute(
    select(HealthMetricEdge)
    .where(HealthMetricEdge.user_id == user_id, HealthMetricEdge.source_metric_id == metric_id)
    .order_by(desc(HealthMetricEdge.confidence))
)
```

## Verification
- Subgraph returns correct nodes/edges for given depth
- Event group linking creates correct number of edges (n*(n-1)/2)
- Neighbor queries return ordered by confidence
- Statistics match manual counts
- Cross-user isolation maintained

## Related Files
- `app/metrics/graph_service.py`
- `app/metrics/models.py`
- `app/metrics/schemas.py`
- `app/metrics/types.py`
