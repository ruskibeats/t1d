---
name: "fix-alembic-async-sqlalchemy"
description: "Fix Alembic migration configuration when the application uses an async SQLAlchemy driver (asyncpg, aiosqlite). Alembic runs DDL synchronously and requires a sync engine — strip the async driver suffix from the connection string and use create_engine instead of async_engine_from_config. Use when alembic upgrade head fails with greenlet/asyncpg errors or asyncio.run() crashes."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Fix Alembic for Async SQLAlchemy Driver

## When to Use

A FastAPI/SQLAlchemy project uses an async driver such as asyncpg (+asyncpg suffix) or aiosqlite (+aiosqlite suffix) for the database connection, and `alembic upgrade head` fails with one of:

- ModuleNotFoundError: No module named greenlet
- RuntimeError: asyncio.run() cannot be called from a running event loop
- DDL statements crash because Alembic tries async operations for schema changes

This happens because the default Alembic template uses an async engine, which requires greenlet and can conflict with already-running async event loops (common in FastAPI reload mode).

Use this skill when:
- Converting a project from sync SQLAlchemy to async
- Migrations start failing after adding an async driver suffix to the connection string
- Greenlet-related errors appear during migration

Do NOT use when:
- The app uses sync SQLAlchemy (no async driver suffix) — vanilla `alembic init` works fine
- The async Alembic runner already works (greenlet is installed and no event loop conflicts)

## Procedure

### Step 1 — Replace imports

In `alembic/env.py`:

Remove:
- `import asyncio`
- `from sqlalchemy.ext.asyncio import async_engine_from_config`

Add:
- `from sqlalchemy import create_engine`

Keep `from sqlalchemy import pool` if `pool.NullPool` is referenced in the code.

### Step 2 — Sanitize the connection string

The project sets the connection string via an environment variable (typically loaded from .env) and/or via `alembic.ini`. Both may contain the async driver suffix. Strip it from both sources:

Use `str.replace("+asyncpg", "").replace("+aiosqlite", "")` on the raw connection string value before passing it to Alembic. Apply this to:
- The environment variable (call `load_dotenv()` first so .env is loaded)
- The `alembic.ini` default `sqlalchemy.url` value

**Rationale**: `create_engine` with an async driver suffix tries to use the async driver in synchronous mode, which requires greenlet. Stripping the suffix forces the standard sync driver for the dialect.

### Step 3 — Rewrite run_migrations_online

Remove the async wrapper entirely. Replace with a straightforward sync equivalent:

- Use `create_engine(url, poolclass=pool.NullPool)` instead of `async_engine_from_config(...)`.
- Use `with engine.connect() as connection:` (sync context manager) instead of `async with connectable.connect()`.
- Call `do_run_migrations(connection)` directly instead of `await connection.run_sync(...)`.
- Call `engine.dispose()` directly instead of `await connectable.dispose()`.

### Step 4 — Leave offline mode unchanged

It only generates SQL text — no database connection, no changes needed.

### Step 5 — Verify

Run `alembic upgrade head --sql` for an offline dry run, then `alembic upgrade head` to apply migrations.

## Pitfalls

### Both sources need sanitizing

The environment variable overrides the alembic.ini default. Sanitize both — if the env var is absent, the unsanitized ini default will be used and cause greenlet errors.

### load_dotenv() must run before env var reads

Place `load_dotenv()` right after the imports in `env.py`. Without it, environment variables from `.env` are invisible and Alembic silently falls back to the ini default.

### poolclass=pool.NullPool prevents stale connections

Always pass `poolclass=pool.NullPool` to `create_engine`. Connection pooling across migration steps can cause SSL/connection-closed errors on long-running migrations.

### Only Alembic's env.py changes

The FastAPI application continues using async SQLAlchemy normally. Test by starting the app and querying the database.

### Rare case: when async Alembic is actually needed

Only if migrations run programmatically from async code or use `await` in migration logic. For standard CLI `alembic upgrade head`, the sync approach is simpler.

## Verification

```bash
# Offline dry run
alembic upgrade head --sql

# Online migration
alembic upgrade head
# Expect: INFO  [alembic.runtime.migration] Running upgrade ...

# Confirm no async imports remain
grep -n 'async\\|asyncio\\|async_engine' alembic/env.py
# Expect: no matches (comments/docstrings are fine)
```

**Normal case**: `alembic upgrade head` runs successfully.
**Edge case**: No migration files yet — still no errors.
**Near-miss**: Connection string lacks async driver suffix — skip this skill.