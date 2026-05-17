# Test Configuration

## Default: SQLite In-Memory

By default, all tests run against an in-memory SQLite database:

```bash
python3 -m pytest tests/ -q
```

No external services needed. PostgreSQL type compatibility patches
in `tests/__init__.py` handle JSONB, ENUM, and BIGINT types for SQLite.

> **Known limitation:** SQLite creates only a subset of domain tables
> (core chat + pattern + food tables) to avoid duplicate-index-name
> errors from unrelated domain models. Integration routes touching
> `health_metrics`, `exercise_entries`, `sleep_entries`, etc. may fail
> when running against SQLite. Switch to Postgres for full-table testing.

## Optional: PostgreSQL Integration Lane

### 1. Start Postgres

```bash
docker compose -f docker-compose.test.yml up -d
```

This starts a Postgres 16 container on port 5432:

| Setting | Value |
|---------|-------|
| Host | localhost |
| Port | 5432 |
| Database | t1d_test |
| User | postgres |
| Password | postgres |

### 2. Install asyncpg

```bash
pip install asyncpg
```

### 3. Run Tests

```bash
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/t1d_test python3 -m pytest tests/ -q
```

### 4. Clean Up

```bash
docker compose -f docker-compose.test.yml down
```

### What Changes

When `TEST_DATABASE_URL` starts with `postgresql`, the test engine:

- Creates **all** tables from `Base.metadata` — no selective subset
- Does **not** use SQLite JSONB/ENUM/BIGINT compat patches (Postgres handles them natively)
- Full table creation means integration routes for all domains work

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_DATABASE_URL` | `sqlite+aiosqlite:///:memory:` | Database connection string for tests |