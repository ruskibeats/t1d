# Fixer — Postgres Test Database

## Task
Add PostgreSQL support to the test infrastructure so integration tests can run against a real Postgres instance, removing the SQLite/JSONB compat workaround.

## Scope
1. **`tests/conftest.py`** — add conditional database URL:
   ```python
   import os
   TEST_DATABASE_URL = os.environ.get(
       "TEST_DATABASE_URL",
       "sqlite+aiosqlite:///:memory:"
   )
   ```
   Use this URL in `db_engine()` fixture instead of hardcoded SQLite.

2. **`docker-compose.test.yml`** — new file with Postgres service:
   ```yaml
   version: "3.9"
   services:
     postgres-test:
       image: postgres:16-alpine
       environment:
         POSTGRES_DB: t1d_test
         POSTGRES_USER: postgres
         POSTGRES_PASSWORD: postgres
       ports:
         - "5433:5432"
   ```

3. **Keep SQLite as default.** The Postgres path is opt-in via env var. Run `Full metadata create_all` when using Postgres.

4. **Update `tests/__init__.py`** compat patches to only apply when using SQLite.

## Verification
```bash
# Default (SQLite) still works
python3 -m pytest tests/ -q

# Postgres path
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/t1d_test python3 -m pytest tests/ -q
```

## Output
- Updated `tests/conftest.py`, `tests/__init__.py`
- New `docker-compose.test.yml`
