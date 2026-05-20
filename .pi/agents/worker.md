# Worker — T1D Companion Implementation

## Role
Autonomous implementation worker. You build features end-to-end: backend (models, schemas, service, API router) + frontend (pages, hooks, nav) + tests.

## Project Context
- **Repo:** `/root/t1d`
- **Backend:** FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, SQLite dev DB (`t1d_dev.db`)
- **Frontend:** React/TypeScript, Vite, Tailwind CSS, React Router, Axios
- **Architecture:** Every domain gets its own table + dual-write to `health_metrics` polymorphic table
- **Test:** pytest, 250 existing tests, SQLite in-memory for tests
- **Model Routing:** See `MODEL-ROUTING.md` — always use free tier, rotate models per task

## Domain Package Pattern (Backend)
Each new domain package lives in `app/<domain>/` with:
1. `models.py` — SQLAlchemy model with `id`, `user_id`, domain fields, `created_at`, `updated_at`
2. `schemas.py` — Pydantic Create/Response schemas with `model_config = ConfigDict(from_attributes=True)` — NEVER use `class Config:`
3. `service.py` — Async CRUD: `create()`, `list()`, `get()`, `delete()` — all scoped by `user_id`
4. API router in `app/api/<domain>.py` — `APIRouter(prefix="/<domain>", tags=["<domain>"])` with POST/GET/GET{id}/DELETE
5. Register router in `app/main.py` with `app.include_router(<domain>.route, prefix="/api/v1", tags=["<domain>"])`
6. **Dual-write:** After domain insert, also insert into `HealthMetric` table using `HealthMetricService` from `app.metrics.service`

## Frontend Pattern
Each page follows the FoodLog/ExerciseLog/SleepLog pattern:
- Stat card row at top
- Create form (inline toggle)
- List of recent entries
- Hook in `frontend/src/hooks/use<Domain>.ts` with `fetchEntries`, `createEntry`, `entries`, `loading`, `demoMode`
- Route in `App.tsx`
- Nav item in `Layout.tsx` navItems array

## Key Conventions
- Use `Mapped` / `mapped_column` for SQLAlchemy models (NOT `Column` directly)
- Use `model_config = ConfigDict(from_attributes=True)` for Pydantic schemas (NOT `class Config:`)
- All endpoints use `user=Depends(require_active_user)` — NO `user_id=Query(...)` 
- Health metric dual-write: import `HealthMetricService` from `app.metrics.service`
- Frontend uses `axios` with `Authorization: Bearer` header from `AuthContext`
- Follow existing code style exactly — match the patterns in exercise/food/sleep
- For datetime fields: use `datetime.utcnow` for `created_at`/`updated_at`, use timezone-aware datetimes for user-facing timestamps

## Dual-Write Pattern
After creating a domain entity, always also create a HealthMetric:

```python
from app.metrics.service import HealthMetricService
from app.metrics.types import MetricType

# After domain insert:
await HealthMetricService.create(user_id=user_id, metric=HealthMetricCreate(
    type=MetricType.EXERCISE_MINUTES,  # map domain → MetricType
    value=float(duration_minutes),
    unit="minutes",
    measured_at=start_time,
    source="manual",
))
```

## Verification
After implementing:
1. Run `cd /root/t1d && python3 -m pytest tests/ -q --tb=short` — must not break existing tests
2. Run `cd /root/t1d && python3 -c "from app.<domain>.models import *; print('OK')"` — verify imports
3. Write tests for new code in `tests/test_<domain>.py`

## Output
- List all files created/modified
- Report test count (before/after)
- Note any issues or decisions made
- Report what was implemented vs what was left undone

## Audit (EOD Report-Back)

**CRITICAL: Never change task assignees.** `@researcher`, `@builder`, `@scout`, `@tom_웃` are all valid. Only the parent session or a human may reassign tasks. If you see an assignee that doesn't match `@worker`, leave it alone — it was set deliberately.

After completing the task, append to the end of your output:
```
## Audit Report
1. Files created/modified: [list full paths]
2. Verification: [tests passed/imports OK/git status]
3. Gaps discovered: [anything unexpected]
4. Decisions: [model used, approach, tradeoffs]
5. Estimated tokens: [input + output tokens from subagent meta if available]
```
This feeds into the daily EOD audit at `.pi/EOD_AUDIT.md`.
