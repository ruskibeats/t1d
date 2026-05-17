---
name: phase3-dexcom-nightscout-v2
description: Implements Dexcom OAuth callback and Nightscout config. Use write() tool for ALL files. Do NOT output code in response text.
model: deepseek/deepseek-v4-flash
context: fork
---

# Phase 3: Dexcom OAuth + Nightscout (v2)

## Task
Implement Dexcom OAuth callback flow and Nightscout configuration API.

## CRITICAL RULES
1. Use the `write()` tool to create/overwrite files. NEVER output code in response text.
2. First read existing files to understand current code.
3. Write each file in ONE write() call.

## Steps
1. Read existing files:
   - `app/api/auth.py`
   - `app/api/users.py`
   - `app/db/models.py`
   - `app/services/dexcom_service.py`
   - `app/services/nightscout_service.py`
   - `app/config.py`

2. Use write() to update `app/api/auth.py` — ADD these routes (don't remove existing):
   - `GET /auth/dexcom/callback` — exchanges code for tokens, stores in User model
   - `GET /auth/dexcom/status` — returns connection status
   - `POST /auth/dexcom/disconnect` — clears tokens
   - `POST /auth/dexcom/refresh` — refreshes access token
   - Import: `from fastapi import Query`

3. Use write() to update `app/api/users.py` — ADD these routes:
   - `POST /api/v1/users/me/nightscout` — configure Nightscout (url + api_token)
   - `GET /api/v1/users/me/nightscout` — get connection status
   - `DELETE /api/v1/users/me/nightscout` — disconnect
   - `POST /api/v1/users/me/nightscout/sync` — manual sync trigger
   - Pydantic models: NightscoutConfig, NightscoutStatus

4. Use write() to update `app/db/models.py` — ADD to User class:
   - `nightscout_url: Mapped[str | None] = Column(String(512), nullable=True)`
   - `nightscout_api_token: Mapped[str | None] = Column(String(255), nullable=True)`
   - `nightscout_connected: Mapped[bool] = Column(Boolean, default=False, nullable=False)`
   - `last_nightscout_sync: Mapped[datetime | None] = Column(DateTime, nullable=True)`

5. Run: `cd /root/t1d && python -c "from app.api.auth import router; print('auth OK')"`
6. Run: `cd /root/t1d && python -c "from app.api.users import router; print('users OK')"`

7. Use write() to save notes to `PHASE3_W7_DEXCOM_NIGHTSCOUT.md`

## Output
Write implementation notes to: `PHASE3_W7_DEXCOM_NIGHTSCOUT.md`
