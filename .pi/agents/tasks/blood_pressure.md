# Build blood_pressure domain package

Build the **blood_pressure** domain package for T1D Companion. This tracks systolic/diastolic BP.

Create these files following EXACTLY the same patterns as `app/exercise/`:

1. `app/blood_pressure/__init__.py` — empty
2. `app/blood_pressure/models.py` — SQLAlchemy model `BloodPressure` with: id, user_id, systolic (float), diastolic (float), measured_at (datetime), source (str, nullable), created_at, updated_at. Use Mapped/mapped_column pattern. FK to users.id. Index on user_id+measured_at.
3. `app/blood_pressure/schemas.py` — Pydantic Create/Response schemas
4. `app/blood_pressure/service.py` — Async CRUD scoped by user_id
5. `app/api/blood_pressure.py` — APIRouter(prefix='/blood-pressure', tags=['Blood Pressure']) with POST/GET/GET{detail}/DELETE using require_active_user and get_db
6. Register router in `app/main.py`
7. Dual-write: After creating, write TWO rows to HealthMetric: BLOOD_PRESSURE_SYSTOLIC (value=systolic) and BLOOD_PRESSURE_DIASTOLIC (value=diastolic)
8. Frontend hook: `frontend/src/hooks/useBloodPressure.ts`
9. Tests: `tests/test_blood_pressure.py` with 8+ tests

Use `python3` not `python`. Run `python3 -m pytest tests/test_blood_pressure.py -q` to verify.
Update progress at: /root/t1d/progress.md
