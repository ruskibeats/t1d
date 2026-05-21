---
name: "t1d-connection-test-script"
description: "Create a unified CGM connection test script that tests both Nightscout (Libre) and Dexcom connectivity. Checks .env config, gracefully skips unconfigured providers, and provides actionable setup guidance."
version: 2
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

When setting up or testing CGM (Continuous Glucose Monitor) connections in the T1D Companion project. Use this procedure whenever a user wants to validate that their Libre (via Nightscout) and/or Dexcom connections are working.

## Procedure
6. **Check the database user record** for persisted connection config — the DB and .env may be out of sync:
   ```bash
   sqlite3 t1d_dev.db "SELECT id, email, ns_url, ns_connected, ns_last_sync, dexcom_token, dexcom_connected, dexcom_last_sync FROM tbl_users;"
   ```
   - `ns_url=None` + `ns_connected=0` means Nightscout was never configured in the app, even if .env has a URL
   - The user may have a Nightscout site externally but never linked it in this app
   - Compare DB fields against .env values to identify the gap (env vs persisted connection)

7. **Triage diagnosis**: If both .env has values and DB has stale/missing data:
   - The connection was likely set up outside the app (external Nightscout site) but never linked in T1D Companion
   - User needs to go through the OAuth/Nightscout linking flow in the app to persist credentials to the DB
   - The `.env` file is for application-level config; the DB stores user-scoped connection data
## Pitfalls

- `python` command is not found — always use `python3`
- `.env` may have placeholder values like `your-dexcom-client-id` — detect these with string matching, don't try to connect
- Nightscout may be open (no API token) or closed (token required) — handle both
- Use `async/await` with proper asyncio event loop management

## Verification

- Script prints clear output per provider: ✅ Pass, ⏭ Skipped, ❌ Failed
- Skipped providers show which env var is missing/placeholder
- Passed providers show data count (e.g., "4.5 mmol/L at 2026-05-20T14:30:00Z")
- Failed providers show the error message from the HTTP call or auth