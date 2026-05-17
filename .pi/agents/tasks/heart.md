# Build heart domain package

Build the **heart** domain package for T1D Companion. This tracks heart rate, resting heart rate, and HRV data.

Create these files following EXACTLY the same patterns as `app/exercise/` (models.py, schemas.py, service.py) and `app/api/exercise.py`:

1. `app/heart/__init__.py` — empty
2. `app/heart/models.py` — SQLAlchemy model `HeartRate` with: id, user_id, heart_rate_bpm (float, nullable), resting_heart_rate_bpm (float, nullable), hrv_ms (float, nullable), measured_at (datetime), source (str, nullable), created_at, updated_at. Use Mapped/mapped_column pattern. FK to users.id. Index on user_id+measured_at.
3. `app/heart/schemas.py` — Pydantic Create/Response schemas with model_config = ConfigDict(from_attributes=True)
4. `app/heart/service.py` — Async CRUD: create(), list(), get(), delete() — all scoped by user_id. Use AsyncSession.
5. `app/api/heart.py` — APIRouter(prefix='/heart', tags=['Heart Rate']) with POST/GET(list)/GET{detail}/DELETE endpoints using require_active_user and get_db
6. Register router in `app/main.py`: import heart module, add `app.include_router(heart.route, prefix='/api/v1', tags=['Heart Rate'])`
7. Dual-write: In the POST endpoint, after creating a HeartRate entry, also write to HealthMetric table — one row per non-null metric (HEART_RATE, RESTING_HEART_RATE, HEART_RATE_VARIABILITY). Import HealthMetricService from app.metrics.service.
8. Frontend hook: `frontend/src/hooks/useHeartRate.ts` following useExercise pattern (entries, loading, demoMode, createEntry, fetchEntries)
9. Tests: `tests/test_heart.py` with 8+ tests using SQLite in-memory, covering create, list, get, delete, dual-write, auth

IMPORTANT: Use `python3` not `python`. Run `python3 -m pytest tests/test_heart.py -q` to verify tests pass.
Update progress at: /root/t1d/progress.md
