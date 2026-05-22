---
name: "fix-alembic-async-env-py"
description: "Fix Alembic env.py for async SQLAlchemy projects: strip async driver suffix (+asyncpg, +aiosqlite), use sync engine for DDL, replace async run_migrations with sync connection, handle both .env override and .ini default URL. Use when Alembic fails with greenlet errors, async_engine_from_config crashes, or 'ModuleNotFoundError: no module named greenlet' during alembic upgrade head."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Fix Alembic env.py for Async SQLAlchemy Projects

## When to Use

- Alembic fails during `alembic upgrade head` with `greenlet` errors or `async_engine_from_config` crashes
- The project uses async SQLAlchemy (`create_async_engine` with an async driver suffix such as `+asyncpg` or `+aiosqlite`)
- The current `alembic/env.py` uses `async_engine_from_config` and `asyncio.run(run_async_migrations())`
- You see errors like: `ModuleNotFoundError: No module named 'greenlet'` or `greenlet.spawn` errors

**Boundary**: This skill is for Alembic migration setup only. If the issue is with the application's async engine at runtime (not Alembic), do not use this skill.

## Procedure

### 1. Identify the async driver suffix

Examine the database URL (from the environment or `alembic.ini`) for async driver suffixes:

- `postgresql+asyncpg://...` — suffix is `+asyncpg`. Sync equivalent uses `psycopg2` (bundled with SQLAlchemy).
- `sqlite+aiosqlite://...` — suffix is `+aiosqlite`. Sync equivalent is the default `sqlite` driver (Python stdlib).

Alembic runs DDL (CREATE TABLE, ALTER TABLE) synchronously. It does not need the async driver at all.

### 2. Strip async suffix from env-provided URL

In `env.py`, after loading the database URL from the environment, call `.replace("+asyncpg", "").replace("+aiosqlite", "")` on it before setting it on `config.set_main_option("sqlalchemy.url", ...)`.

**Why**: If `+asyncpg` remains, SQLAlchemy imports asyncpg's sync-compatibility layer which requires the optional `greenlet` package — a common source of deployment failures.

### 3. Also sanitize the .ini fallback URL

After step 2, read the current value of `config.get_main_option("sqlalchemy.url")` (which may be the `.ini` default) and apply the same `.replace(...)` calls to it. Write the sanitized version back with `config.set_main_option(...)`.

**Why**: If the environment variable is missing (e.g., `load_dotenv()` wasn't called or `.env` is absent), Alembic falls back to the `.ini` default. Without this guard, the fallback URL also crashes.

### 4. Replace imports

Remove:
- `import asyncio`
- `from sqlalchemy.ext.asyncio import async_engine_from_config`

Add:
- `from sqlalchemy import create_engine`

Keep:
- `from sqlalchemy.engine import Connection`
- `from sqlalchemy import pool`

### 5. Replace the async run_migrations with a sync version

Delete the entire `async def run_async_migrations()` function that uses `async_engine_from_config(...)`, `async with connectable.connect()`, `await connection.run_sync(...)`, and `await connectable.dispose()`.

Write a new `run_migrations_online` function:
- Get the URL from `config.get_main_option("sqlalchemy.url")`
- Create a sync engine with `create_engine(url, poolclass=pool.NullPool)`
- Open a connection with `with connectable.connect() as connection:`
- Call `do_run_migrations(connection)` inside the block (no `await`, no `run_sync`)
- Call `connectable.dispose()` after the block

**Why**: `create_engine` (sync) + `with connectable.connect()` replaces the async pattern cleanly. The `do_run_migrations` helper is already sync-compatible — it only calls `context.run_migrations()`.

### 6. Clean up the dispatch

The original `run_migrations_online` was typically just:
```python
def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())
```

After replacing it with the sync version from step 5, the bottom dispatch stays the same:
```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 7. Verify

```bash
# Dry-run in offline mode (no database needed)
alembic upgrade head --sql

# Apply live migration
alembic upgrade head

# Check history
alembic history
```

## Pitfalls

- **Missing `load_dotenv()` call**: If the env var isn't loaded, the `.ini` default is used. Step 3 (sanitizing the `.ini` fallback) is essential to handle this case.
- **`run_async_migrations` referenced elsewhere**: Search the project for calls to `run_async_migrations`. Tests, CI scripts, or helper modules may import it directly.
- **Multiple engine sections in alembic.ini**: If `alembic.ini` defines multiple sections like `[myotherdb]`, each needs the same treatment.
- **Keep `poolclass=pool.NullPool`**: Without it, connections may linger between migration steps and cause locking on PostgreSQL.
- **Autogenerate needs model imports**: If `alembic revision --autogenerate` fails after the change, verify `target_metadata = Base.metadata` is set and models are imported at the top of `env.py`.
- **SQLite edge case**: For `sqlite+aiosqlite://...`, the sync driver is the default `sqlite` (built-in). `.replace("+aiosqlite", "")` produces the correct plain URL.

## Verification

1. `alembic upgrade head` completes without greenlet errors
2. All migration revision files execute successfully
3. `alembic history` shows the expected migration chain
4. Application startup still works (async engine unchanged — only Alembic env.py was modified)
5. `alembic revision --autogenerate -m "test_verify"` produces a valid new revision (delete it afterward)