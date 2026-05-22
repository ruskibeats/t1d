---
name: "fix-alembic-async-engine"
description: "Fix Alembic env.py when the migration engine is configured async (async_engine_from_config with asyncpg) but fails because DDL runs synchronously and the greenlet_spawn dependency is missing. Replace async engine setup with sync create_engine, strip async driver suffices (+asyncpg, +aiosqlite) from the connection URL, and replace run_async_migrations with a sync online runner."
version: 2
created: "2026-05-21"
updated: "2026-05-21"
---
# Fix Alembic env.py: Convert Async Engine to Sync for DDL

## When to Use

- Alembic migrations fail at runtime with errors like `greenlet_spawn has not been called` or `asyncpg requires the greenlet library`
- `alembic upgrade head` fails but the app itself works fine with async SQLAlchemy sessions
- The project uses a FastAPI/SQLAlchemy async engine pattern (e.g., `create_async_engine` with `+asyncpg` or `+aiosqlite`)
- The `alembic/env.py` file uses `async_engine_from_config` and `asyncio.run()` for online migrations

**Do NOT use** when:
- Alembic is already configured with a sync engine and works correctly
- The problem is a different Alembic error (connection refused, missing table, syntax error)

## Procedure

### 1. Identify async patterns in env.py

Look for these imports indicating an async engine setup:
```python
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config
```

And the online migration function typically looks like:
```python
async def run_async_migrations():
    connectable = async_engine_from_config(...)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())
```

### 2. Replace imports

Swap async imports for sync equivalents. Remove:
```python
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config
```
Add:
```python
from sqlalchemy import create_engine
```

Keep `from sqlalchemy import pool` and `from sqlalchemy.engine import Connection` — they work for both sync and async.

### 3. Strip async driver suffix from the connection URL

Alembic runs DDL synchronously, so the connection URL must use a sync driver. The key transformations:

- `postgresql+asyncpg://host/db` → `postgresql://host/db` (drops +asyncpg, defaults to psycopg2)
- `sqlite+aiosqlite:///path` → `sqlite:///path` (drops +aiosqlite, defaults to pysqlite)

The stripping must happen at **two points** in env.py:

First, when reading the env var override (the `sqlalchemy.url` key in `config.set_main_option`). The env var may contain `+asyncpg` or `+aiosqlite` and must be sanitized before being stored.

Second, when the .ini default value is already present in `config`. Even if there is no env var override, the .ini file itself might have an async URL. Convert the `.ini` default as well.

```python
# Step A: sanitize the env var override
raw_url = os.getenv("YOUR_DB_ENV_VAR")
if raw_url:
    cleaned = raw_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    config.set_main_option("sqlalchemy.url", cleaned)

# Step B: sanitize the .ini default
ini_url = config.get_main_option("sqlalchemy.url")
if ini_url:
    config.set_main_option(
        "sqlalchemy.url",
        ini_url.replace("+asyncpg", "").replace("+aiosqlite", ""),
    )
```

> **Why both?** The env var may be absent in some environments (CI, production without .env). The .ini default is always present. If only one is sanitized, the async suffix can slip through in the other path.

### 4. Replace run_async_migrations with sync version

Replace the entire async online migration function:

```python
def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a sync connection."""
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()
```

Key differences from the async version:
- `async with` → `with` (synchronous context manager)
- `await connection.run_sync(do_run_migrations)` → `do_run_migrations(connection)` (no sync wrapper needed on a sync connection)
- `async_engine_from_config(...)` → `create_engine(url, poolclass=pool.NullPool)`
- The `asyncio.run(run_async_migrations())` wrapper is removed entirely

### 5. Clean up

Remove dead imports from step 2. The final file should have no references to:
- `import asyncio`
- `async_engine_from_config`
- `create_async_engine`
- `asyncio.run()`

## Pitfalls
- **Docker containers lack psycopg2**: After converting to a sync engine (stripping `+asyncpg`), the sync `postgresql://` URL defaults to the `psycopg2` driver. If your production container only has `asyncpg` installed, `alembic upgrade head` will fail with `No module named psycopg2`. Either add `psycopg2-binary` to your Dockerfile or run `pip install psycopg2-binary` in the running container before running migrations.
## Verification

1. **Run migrations** — `alembic upgrade head` succeeds without greenlet/async errors
2. **Check revision** — `alembic current` shows the expected head revision
3. **App connectivity** — The app (with async sessions) still connects to the same database
4. **Rollback works** — `alembic downgrade -1` succeeds
5. **No leftover async imports** — grep `env.py` for any remaining async engine references
6. **Test suite** — Any tests that use Alembic migration fixtures still pass