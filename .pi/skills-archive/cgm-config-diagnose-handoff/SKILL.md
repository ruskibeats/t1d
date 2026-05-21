---
name: "cgm-config-diagnose-handoff"
description: "Diagnose an existing CGM data source configuration (Nightscout, Dexcom), trace through the full code path (.env → service → user model → API), document findings (placeholder vs real, runtime vs config, global vs per-user), and create a Clanker Ops task with comprehensive plan for a human team member. Use when a user asks to configure, fix, or investigate a CGM provider and needs a handoff task for a human teammate."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Diagnose CGM Configuration and Handoff to Human Teammate

Investigate an existing CGM data source configuration, trace the full code path, and create a comprehensive handoff task+plan for a human teammate.

## When to Use

- A user says "configure Nightscout" / "set up Dexcom" / "fix CGM connection"
- A user asks to add or investigate a CGM provider configuration and assign it to a human teammate
- You need to investigate what state a CGM provider is actually in (placeholders vs real creds, running vs not)
- You're creating a handoff task with actionable steps for a human (not a subagent) to execute

**Do not use** when:
- Adding a completely new CGM provider type (use `t1d-cgm-provider-integration` instead)
- Creating a connection test script (use `t1d-connection-test-script` instead)
- The task can be fully executed by a subagent (no human handoff needed)

## Procedure

### 1. Investigate Current Configuration State

Check all layers of configuration:

```bash
# 1a. Check .env file for CGM provider variables
grep -i "NIGHTSCOUT\|DEXCOM\|LIBRE" .env

# 1b. Check if provider is running (process + port)
# Nightscout typically runs on port 4000
ss -tlnp | grep 4000
# Or check Docker
docker ps 2>/dev/null || echo "Docker not available"

# 1c. Check docker-compose.yml for the provider
grep -A5 "nightscout\|dexcom" docker-compose.yml 2>/dev/null
```

### 2. Trace the Full Code Path

Read the relevant files in this order to understand the full config flow:

```bash
# 2a. Service class (how provider fetches/configures)
read app/services/nightscout_service.py   # or dexcom_service.py / other provider

# 2b. Sync service (how provider is called)
read app/services/sync_service.py

# 2c. Config (global settings)
read app/config.py

# 2d. User model (per-user overrides)
read app/db/models.py

# 2e. API endpoints
read app/api/cgm.py
read app/api/users.py
```

Key things to identify:
- **Two-level config**: Is there both a global `.env` fallback AND a per-user DB field?
- **Placeholder vs real**: Are the `.env` values real credentials or template defaults?
- **Runtime state**: Is the provider process/Docker container actually running?
- **Code paths**: What service methods use the config? How is it passed?

### 3. Document Findings

Summarize in a compact table:

| Check | Result |
|-------|--------|
| `.env` URL configured | ✅/❌ real or placeholder |
| Provider process running | ✅/❌ |
| Per-user config exists | ✅/❌ (DB field or not) |
| Global fallback configured | ✅/❌ |

Call out any notable architecture details (e.g., "two levels of config: global `.env` fallback + per-user DB field").

### 4. Create Clanker Ops Task for Human Teammate

Create a task with the specific human assignee:

```
todo action="create" subject="[PROVIDER] Configure [ProviderName] for production"
      assigned="tom"  # or appropriate human from roster
      description="..."
```

The description should reference the investigation findings.

### 5. Write Comprehensive Plan

Write a `.pi/todo-plans/#N_plan.md` file covering:

- **Intended Outcome**: What a working configuration looks like
- **Step-by-Step**:
  1. Get actual credentials (Nightscout URL, API token)
  2. Update `.env` with real values
  3. Verify connection (run test script or manual check)
  4. Configure per-user settings if needed
  5. Run sync to confirm data flow
- **Verification**: How to confirm it's working (API test, sync check, live data)
- **Dependencies**: Credentials from user, running provider instance
- **Troubleshooting**: Common issues (wrong port, typo in URL, expired token), with specific diagnostic commands

## Pitfalls

- **Placeholder values**: `.env` defaults often have `your-nightscout-url` type placeholders. Always flag these explicitly — don't assume they're real.
- **Two-level config confusion**: If both `.env` AND a per-user DB field exist, explain which takes precedence and where to configure each.
- **Runtime vs config**: A service can be configured in `.env` but not running. Check both.
- **Docker availability**: The Docker daemon may not be running. Don't suggest Docker commands without checking first.
- **Human team member names**: Use the glyph convention from the roster — `@name_웃` for humans, not `@name`. Check `docs/CLANKER_ROSTER.md` for correct naming.
- **Overwriting real config**: Never modify `.env` with placeholder changes. Only recommend the human set real credentials.

## Verification

1. Task is created with the correct human assignee (not a subagent)
2. Plan file exists at `.pi/todo-plans/#N_plan.md` with all required sections
3. Investigation findings are included in the task description or plan
4. Real vs placeholder credentials are clearly distinguished
5. All referenced file paths exist and were read (not guessed)
6. Diagnostic commands in the plan are concrete (copy-paste ready, with actual paths)