# Todo #4: [GRAPH-D] Add event-group API endpoint + auth for graph endpoints

Status: pending
Tags: #p1 #api #backend #graph
Branch: dad_1805

Add GET /api/v1/metrics/graph/event-group/{event_group_id} endpoint. Replace user_id query params with Depends(require_active_user) on all graph endpoints.
