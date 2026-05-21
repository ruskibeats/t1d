---
name: "dual-write-consolidation-refactor"
description: "Consolidate duplicate dual-write patterns across domain services into a unified registry/facade. Eliminates identical write-domain-table → write-HealthMetric logic across multiple services."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Dual-Write Consolidation Refactor

## When to Use

When multiple domain services contain identical dual-write logic (write domain table → write HealthMetric) that creates maintenance burden, inconsistency risk, and code duplication. Ideal for consolidating 5+ services with the same pattern into a single unified registry.

## Procedure

### 1. Pattern Discovery
```bash
# Find all occurrences of dual-write pattern
rg -l "HealthMetric" app/services/*.py | xargs rg -l "create_health_metric"

# Analyze the pattern across services
rg "write.*health_metric|create_health_metric" app/services/ -A 5 -B 2
```

### 2. Registry Design
Create `app/services/metric_registry.py`:

```python
from typing import Optional, Dict, Any
from app.db.models import HealthMetric, User
from app.db.session import SessionLocal

class MetricRegistry:
    """Central registry for dual-write consolidation."""
    
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
    
    def write_domain_and_metric(
        self,
        domain_obj: Any,
        domain_id_field: str,
        metric_type: str,
        user_id: str,
        event_time: datetime,
        value: float,
        **metric_kwargs
    ) -> Dict[str, Any]:
        """Atomically write domain object and corresponding HealthMetric."""
        # 1. Write domain object
        domain_obj.id = getattr(domain_obj, domain_id_field)
        self.db.add(domain_obj)
        
        # 2. Write HealthMetric
        metric = HealthMetric(
            user_id=user_id,
            metric_type=metric_type,
            value=value,
            recorded_at=event_time,
            **metric_kwargs
        )
        self.db.add(metric)
        
        # 3. Commit both
        self.db.commit()
        
        return {"domain": domain_obj, "metric": metric}
```

### 3. Service Migration
For each service with dual-write:

```python
# Before (in service file)
def create_glucose_reading(user_id, value, recorded_at):
    reading = GlucoseReading(...)
    db.add(reading)
    metric = HealthMetric(user_id=user_id, metric_type="glucose", ...)
    db.add(metric)
    db.commit()

# After
from app.services.metric_registry import MetricRegistry

def create_glucose_reading(user_id, value, recorded_at):
    registry = MetricRegistry(db)
    result = registry.write_domain_and_metric(
        domain_obj=GlucoseReading(...),
        domain_id_field="id",
        metric_type="glucose",
        user_id=user_id,
        event_time=recorded_at,
        value=value
    )
    return result
```

### 4. Gradual Rollout Strategy
1. **Phase 1**: New services use registry immediately
2. **Phase 2**: Migrate highest-traffic services
3. **Phase 3**: Deprecate inline dual-write patterns
4. **Phase 4**: Add linting rule to prevent new dual-writes

### 5. Verification
```python
def test_registry_consistency():
    """Ensure registry produces same results as inline dual-write."""
    # Test data created via both paths
    # Verify identical HealthMetric records
    # Verify foreign key relationships intact
```

## Pitfalls

- **Transaction boundaries**: Registry must handle rollbacks correctly
- **ForeignKey dependencies**: Some metrics reference domain IDs (e.g., event_group_id)
- **Service-specific fields**: Some services need extra metric fields beyond the pattern
- **Backward compatibility**: Old code paths must continue working during migration

## Verification

1. All 16+ services show reduced duplicate code
2. HealthMetric records are identical between old/new approaches
3. Test coverage includes edge cases (failed domain writes, metric write failures)
4. Performance benchmarks show no regression