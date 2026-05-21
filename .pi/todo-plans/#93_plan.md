# Clanker Ops #93: [OPS] LibreLink — verify connection is up and running

Status: in_progress
Owner: @tom_웃
Tags: #p1 #cgm #libre #ops
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #93 is still open, assigned to you, and not blocked.
- Mark #93 in progress before implementation work.
- Read the full plan before editing files.

### While Working
- Keep changes scoped to this task and preserve unrelated user changes.
- Do not create skills, tools, scripts, or extra files unless the operator explicitly requested them or this plan names them.
- If you discover blockers, duplicates, missing context, or follow-up work, add/update Clanker Ops items instead of burying findings in prose.
- If the task cannot be completed, leave it in progress or mark it failed/deferred with a clear reason.

### Before Closing
- Run relevant verification checks.
- Update the Clanker Ops item with a completion summary.
- Include files changed, commands run, verification result, blockers/follow-ups, and estimated token burn.
- Mark the task completed only when the requested work is done and verified.

### Closeout Report Template

```text
Summary:
Files changed:
Commands run:
Verification:
Follow-ups created:
Blockers:
Token burn estimate:
Status:
```

## Plan

### Intended Outcome
- Verify Libre CGM data flows through Nightscout to T1D Companion
- Confirm API endpoint reachable, authentication valid, data syncing

### Current Status
Your Libre CGM data flows through Nightscout. The project has:
- ✅ Nightscout service code ready (`app/services/nightscout_service.py`)
- ✅ Sync integration ready (`app/services/sync_service.py`)
- ❌ Nightscout credentials NOT configured in `.env`

### Steps
1. Add your Nightscout credentials to `.env`:
   ```
   NIGHTSCOUT_URL=https://your-nightscout-url.herokuapp.com
   NIGHTSCOUT_API_TOKEN=your-api-token-here
   ```
   (Leave token empty if your Nightscout is public)

2. Run the test script to verify connection:
   ```
   python scripts/test_nightscout.py
   ```

### Verification
Expected output:
```
✓ Connection successful
✓ Latest reading: {value} mg/dL at {timestamp}
✓ Data count: {n} readings in last 24h
```

### Preserved Previous Plan
Check the LibreLink/LibreLinkUp integration for the T1D Companion system. Verify: (1) API endpoint is reachable, (2) authentication tokens valid, (3) data syncing correctly, (4) any recent service changes broke connectivity. If down, diagnose and restore. This feeds into the CGM data pipeline alongside Dexcom/Nightscout.