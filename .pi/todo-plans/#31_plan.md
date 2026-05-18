# Todo #31: [GRAPH-0.1] Add event_group_id column to health_metrics

Status: completed
Owner: @worker
Tags: #p0 #backend #database #graph
Branch: dad_1805

Add nullable UUID/string event_group_id column to health_metrics table. Add index (user_id, event_group_id). Backfill existing rows as null. Update HealthMetricCreate and HealthMetricResponse schemas. Update HealthMetricService.create() and create_batch().
