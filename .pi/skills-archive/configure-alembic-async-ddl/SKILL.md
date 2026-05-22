---
name: "configure-alembic-async-ddl"
description: "Configure Alembic migrations for async SQLAlchemy applications. Walks through env.py setup: stripping async driver suffix for DDL-compatible sync connections, wiring target_metadata to the actual MetaData object, and using NullPool for migration connections. Use when adding Alembic to a FastAPI/SQLAlchemy project that uses async engines (asyncpg, aiosqlite)."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Configure Alembic DDL Sync for Async SQLAlchemy

## When to Use

Configure Alembic migrations for a project where the application uses **async SQLAlchemy engines** (asyncpg, aiosqlite, etc.) but Alembic needs **synchronous DDL connections**.

Use when:
- Your app uses `create_async_engine` with `+asyncpg` or `+aiosqlite` driver URLs
- You're setting up Alembic `env.py` from scratch
- Existing migrations fail with "no module asyncpg" or greenlet errors inside Alembic
- `alembic check --autogenerate` shows no DDL changes (silent failure: async engine can't detect DDL)

Do NOT use when:
- Your app uses a synchronous SQLAlchemy engine (only sync drivers like `psycopg2`, `pysqlite`)
- You're using third-party migration tools other than Alembic

## Procedure

### Step 1 — Identify your MetaData object

Your models define DDL via a SQLAlchemy `MetaData` object. Export one central instance:

```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

The `Base.metadata` property holds the `MetaData` instance that Alembic needs for autogenerate.

### Step 2 — In env.py, strip the async driver suffix

Alembic runs DDL statements synchronously. Async drivers like `asyncpg` or `aiosqlite` are not compatible with Alembic's `create_engine`. Strip the async suffix from the connection string:

```python
# alembic/env.py
import os
from logging.config import fileConfig
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from alembic import context

from app.db.models import Base

load_dotenv()
config = context.config

# Strip async driver for DDL-compatible sync connection
dsn = os.environ.get("DB_DSN")
if dsn:
    sync_dsn = dsn.replace("+asyncpg", "").replace("+aiosqlite", "")
    config.set_main_option("sqlalchemy.url", sync_dsn)

# Also sanitize the .ini default
ini_dsn = config.get_main_option("sqlalchemy.url")
if ini_dsn:
    config.set_main_option(
        "sqlalchemy.url",
        ini_dsn.replace("+asyncpg", "").replace("+aiosqlite", ""),
    )
```

### Step 3 — Wire target_metadata to your MetaData object

This is the #1 most common mistake. `target_metadata` must be the actual SQLAlchemy `MetaData` object (from `Base.metadata`), NOT the async engine:

```python
target_metadata = Base.metadata   # Correct: MetaData object
```

**WRONG** approaches that silently produce empty migrations:
```python
# target_metadata = async_engine   # No DDL detected
# target_metadata = None           # No autogenerate
```

**Why this matters**: `autogenerate` compares the database schema against `target_metadata` to detect DDL changes. An async engine doesn't expose SQLAlchemy table metadata — `alembic check` runs without errors but reports zero changes. This is a silent failure most easily caught by inspecting the generated revision file.

### Step 4 — Create a sync engine for online migrations

Use `sqlalchemy.create_engine` (synchronous), not `create_async_engine`. Use `NullPool` to avoid connection pooling issues during one-shot migration runs:

```python
from sqlalchemy.engine import Connection

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    dsn = config.get_main_option("sqlalchemy.url")
    connectable = create_engine(dsn, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()
```

### Step 5 — Wire offline and dispatch

Offline mode emits SQL without a database connection. Add it alongside online:

```python
def run_migrations_offline() -> None:
    dsn = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=dsn,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# Dispatch
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Step 6 — Verify with a dry run

```bash
# Check that DDL changes are detected (succeeds with detected changes)
alembic check --autogenerate

# Generate a test migration
alembic revision --autogenerate -m "verify_ddl"

# Inspect the revision — should contain op.create_table / op.add_column, not empty
cat alembic/versions/*verify_ddl*.py

# Dry-run SQL output (offline mode)
alembic upgrade head --sql

# Rollback the test revision
alembic downgrade -1

# Clean up test revision
rm alembic/versions/*verify_ddl*.py
```

## Pitfalls

### target_metadata = Base.metadata, NOT the async engine
The #1 footgun. Setting `target_metadata` to an `AsyncEngine` object silently produces zero autogenerate output — `alembic check` passes but migrations produce empty revisions. Always verify by inspecting the generated revision file content, not just exit codes. Recovery: swap to `Base.metadata`.

### Alembic needs sync drivers installed
Even if your app uses `asyncpg`, Alembic's online mode uses synchronous `psycopg2`. Install it:
```bash
pip install psycopg2-binary  # development
# pip install psycopg2       # production (requires libpq-dev)
```
Without a sync driver, `create_engine` in `run_migrations_online()` raises `ModuleNotFoundError`.

### NullPool for migration connections
Alembic runs migrations as one-shot operations — connection pooling is not beneficial:
- **NullPool**: clean open/close per migration run
- **QueuePool** (default): holds idle connections that may time out during long migration reviews or conflict with async pool resources

### DSN sanitization order matters
Process the env var BEFORE the .ini default. If you process the env var after checking the .ini default, the plain sync DSN from .ini may already be correct but the async env var override gets ignored.

### Async driver in alembic.ini itself
If `sqlalchemy.url` in `alembic.ini` contains `+asyncpg` or `+aiosqlite` directly:
```ini
sqlalchemy.url = postgresql+asyncpg://u:p@localhost/db
```
Always sanitize it in env.py (Step 2). Never expect developers to maintain a separate sync URL manually.

### Greenlet / event loop errors
If you accidentally use `create_async_engine` in env.py, Alembic fails with greenlet errors because `connection.execute()` is called synchronously inside migration loops. Fix: always use synchronous `create_engine`.

## Verification

```bash
# 1. env.py imports without errors
python3 -c "from alembic.config import Config; from alembic import context; print('env.py OK')"

# 2. Autogenerate detects DDL (produces non-empty revision)
alembic revision --autogenerate -m "verify_ddl"
grep -E "op\.(create|add|alter|drop)" alembic/versions/*verify_ddl*.py \
  && echo "PASS: DDL detected" \
  || echo "FAIL: empty revision — check target_metadata"

# 3. Offline SQL is valid DDL
alembic upgrade head --sql | head -20
# Should show CREATE TABLE / ALTER TABLE statements

# 4. Rollback works
alembic downgrade -1

# 5. Clean up test artifacts
rm alembic/versions/*verify_ddl*.py

# 6. Existing tests still pass
python3 -m pytest tests/ -x -q
```