# Batch 3 — Postgres Test Lane

## Status: ✅ Complete

## What Was Created

### 1. `docker-compose.test.yml`
Postgres 16 Alpine container with healthcheck.

| Setting | Value |
|---------|-------|
| Port | 5432 |
| Database | t1d_test |
| User | postgres |
| Password | postgres |

### 2. `tests/conftest.py` — Updated
- Reads `TEST_DATABASE_URL` env var (default: `sqlite+aiosqlite:///:memory:`)
- On Postgres path: creates **all** tables from `Base.metadata` (no selective subset)
- On SQLite path: keeps existing selective-table creation to avoid duplicate-index errors
- No new dependencies — uses `os.environ.get`

### 3. `tests/__init__.py` — Refactored
- Cleaned up duplicate patch definitions
- Added docstring explaining when patches are needed vs Postgres
- Still applies at import time for SQLite path

### 4. `TESTING.md` — New
- Documents default SQLite path and its table-subset limitation
- Documents Postgres integration lane: docker compose → env var → test run → cleanup
- Documents `TEST_DATABASE_URL` env var

## How to Use

```bash
# Start Postgres
docker compose -f docker-compose.test.yml up -d

# Install asyncpg
pip install asyncpg

# Run full test suite against Postgres
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/t1d_test python3 -m pytest tests/ -q

# Clean up
docker compose -f docker-compose.test.yml down
```

## Verification

```text
$ python3 -m pytest tests/ -q
175 passed, 536 warnings in 1.43s
```

Default SQLite path: ✅ No regressions

## Remaining

- `asyncpg` not added to dev dependencies — left as optional install
- No CI test runner configured — just the env var + docker compose setup