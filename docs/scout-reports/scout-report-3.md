# Scout Report #3: [GRAPH-C] Event-group endpoint + auth

## 1. event_group_id in ingestion flows
app/metrics/graph_service.py:157:    async def link_event_group(self, user_id: int, event_group_id: str) -> list[HealthMetricEdge]:
app/metrics/graph_service.py:158:        """Create SAME_EVENT_AS edges between all metrics sharing the given event_group_id.
app/metrics/graph_service.py:166:                HealthMetric.event_group_id == event_group_id,
app/metrics/graph_service.py:184:                evidence={"event_group_id": event_group_id},
app/metrics/service.py:37:            event_group_id=data.event_group_id,
app/metrics/service.py:75:                event_group_id=item.event_group_id,
app/metrics/service.py:186:    async def get_by_event_group(self, user_id: int, event_group_id: str) -> list[HealthMetric]:
app/metrics/service.py:187:        """Return all health metrics for a user belonging to a given event_group_id."""
app/metrics/service.py:191:                HealthMetric.event_group_id == event_group_id,
app/metrics/models.py:44:    event_group_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
app/metrics/schemas.py:12:    event_group_id: Optional[str] = None
app/metrics/schemas.py:22:    event_group_id: Optional[str] = Field(None, description="Identifier for grouping related metric events")
app/metrics/schemas.py:27:    event_group_id: Optional[str] = None
app/metrics/schemas.py:39:    event_group_id: Optional[str]
app/ingestion/fitbit.py:55:                event_group_id=activity_group_id,
app/ingestion/fitbit.py:64:                    event_group_id=activity_group_id,
app/ingestion/fitbit.py:85:                event_group_id=sleep_group_id,
app/ingestion/fitbit.py:94:                    event_group_id=sleep_group_id,
app/ingestion/garmin.py:55:        # Each Garmin activity is a distinct event – assign an event_group_id for all its metrics
app/ingestion/garmin.py:64:            event_group_id=activity_group_id,
app/ingestion/garmin.py:75:                event_group_id=activity_group_id,
app/ingestion/garmin.py:86:                event_group_id=activity_group_id,
app/ingestion/garmin.py:97:                event_group_id=activity_group_id,
app/ingestion/garmin.py:121:        # Each Garmin sleep event is a distinct group – assign a shared event_group_id
app/ingestion/garmin.py:131:            event_group_id=sleep_group_id,
app/ingestion/garmin.py:151:                    event_group_id=sleep_group_id,
app/ingestion/garmin.py:185:                event_group_id=body_group_id,
app/ingestion/garmin.py:197:                event_group_id=body_group_id,
app/ingestion/garmin.py:209:                event_group_id=body_group_id,

## 2. GET /api/v1/metrics/graph/event-group/{id} endpoint

## 3. Auth on graph endpoints (user_id query params)
40:    user_id: int = Query(..., description="User ID (placeholder — replace with auth)", ge=1),
57:    user_id: int = Query(..., ge=1),
76:    user_id: int = Query(..., ge=1),
104:    user_id: int = Query(..., ge=1),
122:    user_id: int = Query(..., ge=1),
142:    user_id: int = Query(..., ge=1),
164:    user_id: int = Query(..., ge=1),
181:    user_id: int = Query(..., ge=1),
210:    user_id: int = Query(..., ge=1),
232:    user_id: int = Query(..., ge=1),
251:    user_id: int = Query(..., ge=1),
270:    user_id: int = Query(..., ge=1),
291:    user_id: int = Query(..., ge=1),

## 4. get_event_group() in graph service
---
app/metrics/graph_service.py
app/metrics/__pycache__/graph_service.cpython-313.pyc

## SUMMARY
- event_group_id: ✅ EXISTS in models (HealthMetric.event_group_id) and used in Fitbit + Garmin ingestion
- Endpoint GET /api/v1/metrics/graph/event-group/{id}: ❌ DOES NOT EXIST — needs creation
- Auth: ❌ ALL graph endpoints in metrics.py still use user_id=Query(...) — 13 routes need migration to require_active_user
- get_event_group(): ✅ EXISTS in metrics service (app/metrics/service.py:186)
- Graph service file: app/metrics/graph_service.py
