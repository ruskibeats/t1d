---
name: "clanker-ops-unknown-agent-diagnosis"
description: "Diagnose 'Unknown agent' errors when dispatching Clanker Ops tasks — agent exists in CLANKER_ROSTER.md but is not registered as a pi subagent. Covers verifying the agent definition, checking subagent registration, and resolving the gap."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

- `clanker dispatch #N` returns "Unknown agent: &lt;name&gt;"
- The agent name was resolved from a task's assignee (`@name`) but pi-subagents rejects it
- You need to understand why a roster-listed agent cannot be dispatched
- You're building dispatch infrastructure and hit the roster-vs-subagent gap

Do **not** use for: generic subagent registration (see `clanker-roster-agent-registration`), dispatch protocol (see `clanker-ops-dispatch-convention`), or task-not-found errors (see `clanker-task-lookup-diagnostic`).

## Procedure

### 1. Confirm the failed dispatch attempt
Look at the error. The `subagent()` call returned a validation/not-found error like:
```
Unknown agent: butler
```
This means the name you passed does not match any registered pi subagent (neither user-scoped, project-scoped, nor packaged).

### 2. Check if the agent exists in CLANKER_ROSTER.md
Search for the agent name in the roster document:
```bash
grep -i -A 10 "^###.*<agent-name>" docs/CLANKER_ROSTER.md
```
Or list all registered agents:
```bash
grep "^### " docs/CLANKER_ROSTER.md
```
If found there but pi-subagents rejects it, you have the classic **roster-vs-subagent gap** — the agent is documented for human assignment but not registered as a pi subagent for machine dispatch.

### 3. Check registered pi subagents
List what pi-subagents actually knows about:
```bash
# List project-scoped agents
subagent({ action: "list", agentScope: "project" })

# List user-scoped agents
subagent({ action: "list", agentScope: "user" })

# List both
subagent({ action: "list", agentScope: "both" })
```
If the agent name doesn't appear anywhere in the output, it's not registered as a subagent.

### 4. Determine the resolution path

**Option A — Agent is described in the roster but meant for human-only dispatch**
Some agents like @butler exist only for human-to-human task assignment on the board. They are not intended for machine dispatch. In this case:
- Do **not** register them as subagents
- Use the plan file's `Execution Protocol` to run the task manually
- Subagent dispatch will not work for these agents

**Option B — Agent should be dispatchable but needs registration**
If the agent has a proper system prompt, role definition, and should be dispatched programmatically:
1. Read the roster entry to extract the role/system prompt
2. Read any skill file the agent references (e.g., `butler` skill at `.agents/skills/project/t1d/butler/SKILL.md` or similar)
3. Register the agent as a pi subagent:
   ```typescript
   subagent({
     action: "create",
     config: {
       name: "butler",
       description: "Role description from roster",
       systemPrompt: "Full system prompt from roster entry / skill file",
       inheritProjectContext: true,
       inheritSkills: true,
       defaultContext: "fresh"
     }
   })
   ```

**Option C — Use intercom to coordinate with a session that can load the agent**
For agents that don't need permanent registration, use intercom to ask a worker session to load the agent definition from its skill file and execute the task:
```
intercom({ action: "send", to: "session-name", message: "Execute butler task: ..." })
```

### 5. Retry dispatch after resolution
Once the agent is registered (Option B) or an alternative path chosen (A or C), retry:
```
subagent({ agent: "butler", task: "task from plan file", ... })
```

## Pitfalls

- **Roster is NOT a subagent registry**: `CLANKER_ROSTER.md` documents ~35 curated agents for human task assignment. Only a fraction are registered as pi subagents. Do not assume roster presence means subagent dispatchability.
- **Agent name case sensitivity**: Subagent names are case-sensitive. The roster might use `butler` but you try `Butler`. Always match exactly.
- **Skill files ≠ subagent definitions**: A skill file (`.agents/skills/`) may describe an agent's behavior but that doesn't register it as a pi subagent. You need `subagent({ action: "create", ... })` separately.
- **Duplicate registration fails**: If you try to create an agent with a name that already exists (even if it's in a different scope), creation will fail. Check both user and project scope first.
- **Agent definition drift**: If you register based on an old roster entry, the role/system prompt may be stale. Always read the latest `CLANKER_ROSTER.md` and referenced skill files.

## Verification

1. **Before**: `subagent({ action: "list" })` — confirm the agent name is **absent**
2. **After registration**: `subagent({ action: "get", agent: "name" })` — confirm the agent is now registered with correct system prompt
3. **Dispatch test**: `subagent({ agent: "name", task: "health check" })` — confirm it responds without "Unknown agent" error
4. **Board test**: Run `clanker dispatch #N` — confirm the full pipeline works end-to-end