# Todo #32: [GRAPH-0.2] Group multi-metric ingestion events

Status: pending
Owner: UNASSIGNED
Tags: graph, backend, p0

## Plan
1. Update meal ingestion to assign one `event_group_id` to CARBS/FAT/PROTEIN/FIBER/CALORIES metrics from the same meal
2. Update exercise ingestion to assign `event_group_id` to workout-derived metrics
3. Update insulin ingestion to assign `event_group_id` to related insulin metrics
4. Update sleep ingestion to assign `event_group_id` to nightly sleep metrics
5. Update Garmin/Fitbit provider ingestion to preserve provider event/session IDs in `event_group_id`
6. Add tests for each grouping scenario

## Verification
- Each ingestion type creates a stable event_group_id
- Metrics from the same event share the same event_group_id
- Tests pass

## Intercom Rules
- If blocked, use `intercom({ action: "reply", message: "BLOCKED: <reason>" })`
- Do NOT silently fail — always report back

## Discovered Work
- If ingestion patterns reveal issues, report via intercom as suggested new todos
