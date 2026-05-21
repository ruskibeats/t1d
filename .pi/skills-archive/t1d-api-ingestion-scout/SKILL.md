---
name: "t1d-api-ingestion-scout"
description: "Trace API endpoint features and their associated backend service/ingestion pipeline logic."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use this procedure when investigating how a specific API endpoint maps to ingested health data or processing services in the T1D Companion codebase.

## Procedure
1. **Find Endpoint**: Search for the API route definition in `app/api/` or `app/main.py`. Note the handler function.
2. **Identify Service**: Follow imports in the handler to find the corresponding service logic in `app/services/`.
3. **Map Ingestion Pipeline**:
   - If it's a retrieval endpoint, identify the data source service (e.g., `dexcom_service.py`, `fitbit.py`).
   - If it's a persistence endpoint, locate the model and repository/CRUD operation (e.g., `app/db/` or model-specific service).
4. **Validate Persistence**: Search the service for persistence patterns (e.g., `upsert`, `save`, `create`) to understand how data matures from ingestion to the database.
5. **Orchestrate Scouts**: If the investigation is complex (involving multiple services or data sources), dispatch a `scout` subagent (`pi subagent single --agent scout --task "..."`) to handle the code-reading while you plan the next step.

## Pitfalls
- Assuming a single service manages the entire pipeline (data often passes through `DataIngestionAgent` or `SyncService`).
- Overlooking middleware (authentication or safety filtering) in `app/api/`.
- Misinterpreting model relationships (e.g., `event_group_id` links metrics across services).

## Verification
- Successfully identified the endpoint entry point.
- Traced the request to the correct service logic.
- Confirmed the data ingestion or persistence source.