---
name: graph-event-group-testing
description: Test event grouping, same-event edge deduplication, and link_event_group functionality in the health metrics graph.
---

# Graph Event Group Testing

## Purpose
Test event grouping, same-event edge deduplication, and link_event_group functionality.

## When to Use
When implementing event_group_id feature or verifying event grouping behavior.

## Procedure

### 1. Test event_group_id queries
```python
@pytest.mark.asyncio
async def test_event_group_id_queries(db_session, test_user):
    """Test querying metrics by event_group_id."""
    service = HealthMetricService(db)

    # Create metrics with same event_group_id
    for i in range(3):
        await service.create(
            user_id,
            HealthMetricCreate(
                type=MetricType.CARBS if i == 0 else (MetricType.PROTEIN if i == 1 else MetricType.FAT),
                value=30.0 + i * 10,
                unit="g",
                measured_at=datetime.now(timezone.utc),
                source="test",
                event_group_id="meal-123",
            ),
        )

    # Query by event_group_id
    from sqlalchemy import select
    from app.metrics.models import HealthMetric
    result = await db.execute(
        select(HealthMetric).where(
            HealthMetric.user_id == user_id,
            HealthMetric.event_group_id == "meal-123"
        )
    )
    metrics = result.scalars().all()
    assert len(metrics) >= 3
```

### 2. Test same-event edge deduplication
```python
@pytest.mark.asyncio
async def test_same_event_edge_deduplication(db_session, test_user):
    """Test that same_event_as edges are deduplicated."""
    service = HealthGraphService(db)

    # Create two metrics with same event_group_id
    metric1 = await HealthMetricService(db).create(...)
    metric2 = await HealthMetricService(db).create(...)

    # Create edge manually
    edge1 = await service.upsert_edge(...)

    # Try to create duplicate edge
    edge2 = await service.upsert_edge(...)

    assert edge1.id == edge2.id
```

### 3. Test link_event_group creates all pairwise edges
```python
@pytest.mark.asyncio
async def test_link_event_group_creates_edges(db_session, test_user):
    """Test link_event_group creates all pairwise edges."""
    # Create 4 metrics with same event_group_id
    metrics = []
    for i in range(4):
        m = await HealthMetricService(db).create(...)
        metrics.append(m)

    service = HealthGraphService(db)
    edges = await service.link_event_group(user_id, "multi-meal")

    # 4 metrics should create 6 pairwise edges (combination of 4 taken 2 at a time)
    assert len(edges) == 6
```

## Verification Checklist
- [ ] Event group queries return all metrics in group
- [ ] Same-event edges are deduplicated
- [ ] link_event_group creates correct number of edges
- [ ] Tests cover all event grouping paths

## Related Files
- `tests/test_graph_event_grouping.py`
- `app/metrics/graph_service.py`
- `app/metrics/schemas.py`
