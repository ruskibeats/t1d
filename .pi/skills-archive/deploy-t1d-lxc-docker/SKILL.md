---
name: "deploy-t1d-lxc-docker"
description: "Deploy T1D Companion code changes to LXC docker-compose environment: commit/push, pull on LXC, fix Docker build (LICENSE), fix alembic env.py for sync DDL, run migrations, fix schema drift, restart app, and verify with a smoke test curl."
version: 2
created: "2026-05-21"
updated: "2026-05-21"
---
# Deploy T1D Companion to LXC Docker Environment

## When to Use
After making code changes (new migrations, new modules, model changes) that need to go live on the LXC docker-compose deployment at sparkyfitness.

## Prerequisites
- Changes committed and pushed to GitHub
- Root SSH access to sparkyfitness LXC
- Docker and docker-compose installed on LXC

## Procedure
### 0. Full reset for deep schema drift (first resort, not last)
If schema drift is deep (multiple missing columns, enum conflicts, stale migration state), skip incremental fixes:

```bash
docker-compose down -v    # Wipes postgres_data volume
docker-compose up -d      # Fresh build with clean DB
# Wait for healthy, then:
docker-compose exec app alembic upgrade head
```

Then create a test user and proceed. This avoids layers of ALTER TABLE surgery.

### 0a. Remove uvicorn --reload before deploying code
If `docker-compose.yml` uses `--reload` (hot-reload), remove it first. Hot-reload kills uvicorn mid-request when `docker cp` triggers file changes, causing PendingRollbackError cascade on all subsequent requests.

Change:
```yaml
command: sh -c "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```
To:
```yaml
command: sh -c "uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

After deployment, restart the container instead of relying on hot-reload:
```bash
docker-compose restart app
```
## Pitfalls
- **Stale container code**: `docker-compose exec` runs inside the *running* container with *old* code. Must rebuild (`docker-compose build`) or manually copy new files with `docker cp`.
- **Slow Docker builds**: pip install . can take 3-5 minutes. If the build times out, copy files manually and pip install only changed dependencies.
- **Transaction rollback**: Alembic runs migrations in a transaction. If any step fails, ALL prior steps in that migration roll back. Always check `alembic_version` table, not just table existence.
- **ENUM types in PostgreSQL are schema-level objects**: If a migration's CREATE TABLE defines a column with postgresql.ENUM, that creates the type. If another migration or the SA model's column also uses that ENUM type, it fails with "already exists". Fix: use `create_type=False`.
- **passlib + bcrypt**: Latest bcrypt breaks passlib. Pin to bcrypt==4.0.1.
- **asyncpg URL in Alembic**: must strip `+asyncpg` suffix and use sync `create_engine`.

## Verification
- `docker-compose ps` shows `Up (healthy)` for all services
- Alembic head matches expected revision
- All expected tables exist: `\dt` in postgres
- Smoke test curl returns 200 with valid response
- Login works (no bcrypt error)
- Simulator creates a run successfully