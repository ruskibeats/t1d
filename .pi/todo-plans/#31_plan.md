# Todo #31: [GRAPH-0.1] Add event_group_id column to health_metrics

Status: pending
Owner: UNASSIGNED
Tags: graph, backend, database, p0

## Plan
1. Add nullable UUID/string `event_group_id` column to `health_metrics` table via Alembic migration
2. Add index `(user_id, event_group_id)`
3. Backfill existing rows as null
4. Update `HealthMetricCreate` and `HealthMetricResponse` schemas in `app/metrics/schemas.py`
5. Update `HealthMetricService.create()` and `create_batch()` in `app/metrics/service.py`
6. Run `alembic upgrade head` and verify
7. Run tests: `pytest tests/ -q -k "metric" `

## Verification
- Migration applies cleanly
- New column exists and is nullable
- Index created on (user_id, event_group_id)
- Tests pass

## Intercom Rules
- If blocked, use `intercom({ action: "reply", message: "BLOCKED: <reason>" })`
- Do NOT silently fail — always report back

## Discovered Work
- If schema changes reveal issues, report via intercom as suggested new todos
