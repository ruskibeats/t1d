---
name: "explore-t1d-architecture"
description: "Navigate the T1D Companion codebase: trace SQLAlchemy models, entity relationships, the health metrics graph, enum types, and pattern detection algorithms across app/* directories."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

Use this skill when you need to quickly understand or navigate the T1D Companion backend architecture — specifically to find SQLAlchemy ORM models, trace entity relationships, explore the health metrics graph (nodes/edges), discover MetricType/GraphEdgeType enums, or locate pattern detection algorithms (post-meal spikes, overnight hypoglycemia, exercise impact, etc.).

---

## Procedure

### 1. Find All Model Files

Scan for SQLAlchemy model definitions across the modular app/ subpackages:

```bash
# Find all models.py files (each app/ subpackage may have one)
find app/ -name 'models.py' | sort

# Find all schema/type definitions
find app/ -name 'types.py' -o -name 'schemas.py' | sort
```

Key locations:
- `app/db/models.py` — legacy central models (GlucoseReading, ContextEvent, User, Conversation, etc.)
- `app/db/base.py` — DeclarativeBase
- `app/metrics/models.py` — HealthMetric + HealthMetricEdge (graph store)
- `app/{activity,blood_pressure,exercise,food,heart,lifestyle}/models.py` — domain-specific models
- `app/models/{glucose,event,chat,insight}.py` — older Pydantic models / schemas

### 2. Trace Entity Relationships

Start with the base model class and work outward:

```bash
# Show column definitions and relationships
grep -n 'class \|Column\|relationship\|ForeignKey\|Mapped\[' app/db/models.py | head -60
grep -n 'class \|Column\|relationship\|ForeignKey\|Mapped\[' app/metrics/models.py | head -40

# Find references to a specific table across the codebase
rg -n 'GlucoseReading' app/ --include '*.py' | head -20
rg -n 'HealthMetric' app/ --include '*.py' | head -20
```

### 3. Explore the Health Metrics Graph

The graph store uses `HealthMetric` (node) and `HealthMetricEdge` (directed edge) tables:

```python
# app/metrics/types.py — central enum definitions
class MetricType(StrEnum):  # node types: glucose_reading, meal, exercise, insulin...
class GraphEdgeType(StrEnum):  # edge types: meal_to_glucose_spike, exercise_to_glucose_drop...
```

```bash
# Extract all enum values
rg -A 20 'class GraphEdgeType' app/metrics/types.py
rg -A 30 'class MetricType' app/metrics/types.py
```

The graph service lives at `app/metrics/graph_service.py` — look for:
- `add_edge()` — create relationships
- `query_edges()` — traverse relationships
- `get_neighborhood()` — n-hop neighborhood queries

### 4. Find Pattern Detection Algorithms

Pattern detection is in `app/services/pattern_service.py`. Core algorithms:

```bash
rg -n 'async def detect_|algorithm=' app/services/pattern_service.py
```

Known algorithm identifiers:
- `pattern_service.post_meal_spike.v1` — post-meal glucose spike detection
- `pattern_service.overnight_hypo.v1` — overnight hypoglycemia detection
- `pattern_service.exercise_impact.v1` — exercise effect on glucose
- `pattern_service.delayed_high_fat.v1` — delayed high-fat meal effects

### 5. Trace Service → Agent → API Layers

```bash
# Find which agent coordinates which service
rg -n 'PatternAgent\|DataIngestionAgent\|ConversationAgent' app/agents/ --include '*.py'

# Find API endpoints
find app/api/ -name '*.py' | sort
rg -n 'router\.(get|post|put|delete)' app/api/ --include '*.py'
```

---

## Pitfalls

- **Two model layers**: `app/db/models.py` has legacy models (GlucoseReading, ContextEvent). `app/metrics/models.py` has the newer graph-based store (HealthMetric, HealthMetricEdge). The graph is the *current* data architecture; old models may only exist for backward compatibility or migration.
- **Subpackage models**: Each `app/{activity,blood_pressure,exercise,food}/` subpackage has its own `models.py` — don't assume everything is in `app/db/`.
- **Enum in PostgreSQL**: `MetricType` and `GraphEdgeType` are backed by PostgreSQL ENUM types — adding new values requires a migration (`ALTER TYPE ... ADD VALUE`).
- **`python3` not `python`**: This system has only `python3` available.
- **Use `rg` (ripgrep), not plain `grep`**, for recursive searches — it respects `.gitignore` by default and is much faster.

---

## Verification

- Can find all model files in under 10 seconds using `find app/ -name 'models.py'`
- Can list all `GraphEdgeType` and `MetricType` enum values with one `rg` call each
- Can identify all pattern detection algorithms and their `algorithm=` identifiers
- Can trace from an API endpoint through a service to the underlying database model