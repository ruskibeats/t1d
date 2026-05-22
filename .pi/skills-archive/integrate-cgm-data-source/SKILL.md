---
name: "integrate-cgm-data-source"
description: "Integrate a new CGM data source into the T1D Companion. Add a glucose provider by creating the API service class, DB fields, API endpoints, background sync wiring, and Pydantic schemas. Use when adding a new CGM source like Dexcom, Nightscout, LibreLinkUp, Medtronic, or Eversense."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

Integrate a new CGM (continuous glucose monitor) data source into the T1D Companion. Use when adding a new glucose provider like Dexcom, Nightscout, LibreLinkUp, Medtronic, or Eversense. This covers the full pattern: API service class → DB model fields → Pydantic schemas → API endpoints → background sync wiring.

Do NOT use for:
- Adding a non-CGM health data source (e.g. Fitbit steps, sleep trackers — use the unified health metrics pattern instead)
- Modifying an existing CGM source (fixing bugs, adding features)
- Simple CRUD domain additions (water, mood, fasting — those follow a simpler service+API pattern)

## Procedure

### 1. Add Database Fields to User Model

In `app/db/models.py`, add columns to the `User` class for the new source's connection credentials:

**Credential fields** — nullable String columns (use String(255) for basic fields, String(512) for encrypted values)
**Connection status flag** — Boolean, default=False
**Last sync timestamp** — DateTime, nullable

```python
# Pattern (app/db/models.py, inside class User(Base)):
<source>_email: Mapped[str | None] = Column(String(255), nullable=True)
<source>_connected: Mapped[bool] = Column(Boolean, default=False, nullable=False)
last_<source>_sync: Mapped[datetime | None] = Column(DateTime, nullable=True)
```

Use `Mapped[str | None]` for nullable fields and `Mapped[bool]` for the connected flag.

### 2. Create Pydantic Connection Models

In `app/models/user.py`, add:

- **Connection detail model**: exposes `connected`, credential-adjacent fields (URL, email, region), `last_sync`
- **Test result model**: `success`, `message`, optional `latest_value`, `readings_count`, etc.
- **Reference** in `CGMConnectionStatus` (add a typed field with `Field(...)` descriptor)

### 3. Create the API Service Class

Create `app/services/<source>_service.py` with these required components:

**Custom exception:**
```python
class LibreLinkUpServiceError(Exception):
    """Raised when <Source> API communication fails."""
    pass
```

**Reading Pydantic model** for the external API's reading format:
- Parse timestamps from the raw API format into `datetime`
- Add a `from_api(cls, data: Dict[str, Any])` classmethod for transformation

**Service class** with at minimum these methods:

| Method | Purpose |
|--------|---------|
| `__init__(self, ...)` | Accept connection parameters (email, region, etc.) |
| `login(self)` | Authenticate with the external API, return/store auth ticket |
| `ensure_authenticated(self)` | Guard — login if no valid session exists |
| `get_glucose_readings(self, max_count=100)` | Fetch readings from the source API |
| `sync_glucose_data(self, session, user, lookback_hours=24)` | Fetch + write to DB with dedup |
| `sync_recent_data(self, session, user)` | Lightweight sync (~1h lookback) |

Key implementation patterns:
- Use `httpx.AsyncClient` for all HTTP calls
- Maintain internal auth state (`self._auth_ticket`, `self._user_id`) to avoid re-login on each call
- Handle region redirection: external APIs may redirect to a different regional endpoint
- Log every major step (`self.logger.info(...)`) for debugging
- Parse custom timestamp formats carefully — CGM APIs use non-standard formats (US date `M/D/YYYY H:MM:SS AM/PM`, milliseconds since epoch, etc.)

### 4. Wire Sync into GlucoseReading Writeback

In `sync_glucose_data()`, implement deduplication:

```python
from sqlalchemy import select

# Get existing timestamps to avoid duplicates (scope to today)
existing = await session.execute(
    select(GlucoseReading.timestamp).where(
        GlucoseReading.user_id == user.id,
        GlucoseReading.source == "<source_tag>",
        GlucoseReading.timestamp >= cutoff.replace(hour=0, minute=0, second=0),
    )
)
existing_timestamps = set(existing.scalars().all())

# Build GlucoseReading instances, skipping existing + out-of-range
for reading in raw_readings:
    reading_time = reading.timestamp.replace(tzinfo=None)
    if reading_time in existing_timestamps:
        continue
    if reading_time < cutoff.replace(hour=cutoff.hour - lookback_hours):
        continue
    
    db_reading = GlucoseReading(
        user_id=user.id,
        glucose_value=reading.value_mg_dl,
        glucose_units="mg/dL",
        timestamp=reading_time,
        reading_type="sensor",
        source="<source_tag>",         # e.g. "libre", "dexcom", "nightscout"
        source_device_id="<service>",  # e.g. "librelinkup", "dexcom", "nightscout"
        trend=trend_description,
        trend_rate=None,
        is_calibration=False,
        is_filtered=False,
        confidence_level=100,
    )
    new_readings.append(db_reading)

# Commit once — add each, then commit
if new_readings:
    for r in new_readings:
        session.add(r)
    await session.commit()
```

### 5. Wire into Sync Service

In `app/services/sync_service.py`, make three changes:

**Import** the new service and its error class at the top:
```python
from app.services.librelinkup_service import (
    LibreLinkUpService,
    LibreLinkUpServiceError,
)
```

**In `_sync_user_glucose_async()`**, add an `elif source == "<source_tag>"` block after the existing blocks:
```python
elif source == "librelinkup":
    email = user.librelinkup_email
    region = user.librelinkup_region or "EU2"

    if not email:
        logger.warning(f"LibreLinkUp not configured for user {user_id}")
        return { "user_id": ..., "success": False, "error": "Not configured" }

    service = LibreLinkUpService(email=email, region=region, ...)
    try:
        new_readings = await service.sync_recent_data(session, user)
        user.last_librelinkup_sync = datetime.now(timezone.utc)
        await session.commit()
    except LibreLinkUpServiceError as e:
        logger.error(f"LibreLinkUp sync failed for user {user_id}: {e}")
        return { "user_id": ..., "success": False, "error": str(e) }
```

**In `_sync_all_users_glucose_async()`**, add source detection:
```python
if user.librelinkup_connected and user.librelinkup_email:
    sources.append("librelinkup")
```

### 6. Add API CRUD Endpoints

In `app/api/users.py`, add four endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/me/<source>` | Return connection status (connected flag, email, region, last_sync) |
| POST | `/me/<source>` | Configure and test connection — calls `login()` before saving |
| DELETE | `/me/<source>` | Disconnect — null out credentials, set `connected=False` |
| POST | `/me/<source>/sync` | Trigger manual sync — instantiate service, call `sync_glucose_data()`, update `last_<source>_sync` |

Pattern for connect endpoint (test before save):
```python
@router.post("/me/<source>")
async def configure_<source>(
    config: <Source>Config,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    service = <Source>Service(email=config.email, region=config.region, ...)
    try:
        await service.login()  # Test connection before persisting
    except <Source>ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user.<source>_email = config.email
    user.<source>_connected = True
    await session.commit()
    return {"message": "Connected successfully"}
```

### 7. Update UserResponse Pydantic Schema

In `app/models/user.py`, add new fields to `UserResponse`:
- `<source>_connected: bool = Field(False, ...)`
- `last_<source>_sync: datetime | None = Field(None, ...)`
- Any credential-adjacent public fields (region, URL, email)

### 8. (Optional) Wire into Frontend Settings UI

In `frontend/src/pages/Settings.tsx`, add UI controls for the new source following the existing CGM source patterns.

## Pitfalls

- **Region-specific endpoints**: CGM APIs often have regional variants (EU, EU2, US, AP, JP, etc.). Default to a sensible region (e.g. EU2) and handle redirect detection at login time — the API may respond with a `redirect` field indicating the correct region.
- **Custom timestamp formats**: External APIs rarely use clean ISO 8601. LibreLinkUp uses US-format (`5/20/2026 11:27:23 AM`). Try ISO first as a fast path, then fall back to format-specific parsing with `strptime`. Wrap the whole thing in try/except and log warnings for unparseable rows.
- **Auth token expiry**: Always call `ensure_authenticated()` before data retrieval. For OAuth2 sources (Dexcom), implement full token refresh with `refresh_access_token()`. For token-based auth (Nightscout, LibreLinkUp), just ensure the session is alive.
- **API version headers**: Services like LibreLinkUp require a `version` header. If the version is too old, the API returns `status 920` with a `minimumVersion` field. Read and apply it from the error response.
- **Dedup window scope**: Scope dedup to today's readings only (midnight cutoff). Readings from prior days won't be in the fetch window anyway, so broad dedup is wasteful and error-prone.
- **Commit discipline**: Add all new readings to the session with `session.add(r)`, then commit once. Do NOT commit inside the loop — partial commits on error leave inconsistent state.
- **Source tag consistency**: The `GlucoseReading.source` value must be the same everywhere (service class, sync service, queries). Choose a short unambiguous tag like `"libre"`, `"dexcom"`, `"nightscout"`.
- **Null-safe guards**: Always check `if not user.<source>_email` before attempting sync. The connected flag and credential fields can get out of sync.
- **Credential storage**: Use a String column long enough for encrypted values (String(512)). Credentials should be encrypted in production using `app.core.security` utilities.
- **Celery task reuse**: The sync service uses Celery async tasks. The background task calls `_sync_user_glucose_async()` which handles all sources in one function. Add your source as a new `elif` branch, keeping the pattern parallel to existing ones.

## Verification

1. **Connection test**: POST `/me/<source>` with valid credentials → expect 200 with `{"message": "Connected successfully"}`
2. **Status check**: GET `/me/<source>` → expect `{"connected": true, "<field>": "<value>", "last_sync": null}`
3. **Manual sync**: POST `/me/<source>/sync` → expect 200 with `{"readings_imported": N}` where N > 0
4. **DB persistence**: Query `SELECT * FROM tbl_glucose_readings WHERE source='<source_tag>' AND user_id=<id>` → expect rows returned
5. **Duplicate safety**: Call sync twice → second call returns 0 new readings (or fewer than the first)
6. **Disconnect**: DELETE `/me/<source>` → GET status → `connected: false`, all credential fields null
7. **Background sync**: Trigger the Celery task `sync_all_users_glucose` and verify new readings appear
8. **Error handling**: POST with bad credentials → expect 400 with meaningful error message