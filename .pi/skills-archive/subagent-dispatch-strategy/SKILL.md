---
name: subagent-dispatch-strategy
description: Dispatch subagents for read-only/scout tasks; execute implementation work directly in the parent session. Validates models for tool-calling capability during configuration. Use whenever orchestrating multi-step work involving subagent dispatch.
version: 6
created: 2026-05-19
updated: 2026-05-19
---
# Subagent Dispatch Strategy

## When to Use

Use this skill when orchestrating multi-step work that involves dispatching subagents. It helps decide:

- **Subagent**: Read-only tasks (scouting, research, codebase analysis, file listing, audits)
- **Parent session (direct execution)**: Implementation tasks (code changes, file edits, test writing, graph edge wiring)

Also use when validating a new LLM model for subagent tool-calling capability (e.g., testing free OpenRouter models).

**Trigger phrases**: "dispatch subagents", "orchestrate tasks", "parallel execution subagents", "test model tool calling", "validate LLM model for agents", "worker not executing tools"

## Procedure
### Step 1: Enable skill inheritance

Subagents default to `inheritSkills: false` — they cannot access parent session skills (e.g., project-specific skills, coding conventions, specialized detection patterns). **This is the most common config gap found in practice.** Always set `inheritSkills: true` in the subagent config:

```typescript
subagent({
  name: "scout",
  config: {
    inheritSkills: true,   // REQUIRED — grants access to discovered skills catalog
  },
  task: "..."
})
```

**Why this matters**: Without it, subagents cannot read skills like `graph-edge-wiring-pattern-detection` or `full-output-enforcement`. They operate with only the base system prompt and lose access to project-specific procedural knowledge.

**Detection**: If a subagent produces generic output instead of following project-specific patterns, check whether `inheritSkills: true` is set.

**Distinction from `inheritProjectContext`**: `inheritProjectContext: true` (another common setting) inherits project instruction files like `AGENTS.md` or `CLAUDE.md`. `inheritSkills: true` inherits Pi's discovered skills catalog. Set both when the subagent needs full project context and tooling knowledge. Builtin agents (scout, worker, researcher) default to `inheritProjectContext: true` but `inheritSkills: false`.

### Step 2: Configure subagent with proper tools (The Trilogy)

Before dispatching a subagent, ensure it has all three of these configured:

**2a. Shell tools** — For filesystem tasks:

```
config: {
  tools: "bash,find,ls,grep"       // researcher/scout (read-based tasks)
  // OR
  tools: "bash,todo"               // worker (implementation tasks)
}
```

Without `bash`, `find`, `ls`, `grep` tools, subagents cannot navigate the filesystem.
**Researcher without bash is nearly useless** — it will read files but never execute shell commands.

**2b. Intercom reply mechanism** — For escalation when stuck:

Subagents running in **non-interactive mode** cannot process open-ended intercom replies. They loop infinitely waiting for a response they can't read.

The fix: in each subagent's instructions or system prompt, add:

```
When you need help from the parent session:
- Call intercom({ action: "reply", message: "BLOCKED: <reason>" })
- Always prefix the message with "BLOCKED:" so the parent knows to intervene
- Do NOT call intercom({ action: "send" }) without the "BLOCKED:" prefix
- Only one "BLOCKED:" reply per task — if already blocked, wait
```

The keyword "BLOCKED:" convention lets the parent session distinguish routine updates from escalation requests.

**2c. Todo tool** — For self-management:

Subagents should be able to read plan files and update their own status. Add to the agent's instructions:

```
After being dispatched, use the todo tool to manage your state:
- todo({ action: "read", ... }) the plan file at .pi/todo-plans/#<id>_plan.md
- todo({ action: "update", id: <n>, status: "in_progress" }) when starting
- todo({ action: "update", id: <n>, status: "completed" }) when done
- If you discover additional work, create new pending todos
```

This reduces parent-session overhead from manually tracking every subagent's status.
## Pitfalls
### Async subagent dispatch is unreliable for implementation

Tested across 6+ models (ling-2.6-flash, gpt-oss-120b, laguna-m.1, trinity-large-thinking, cobuddy, deepseek-v4-flash). All non-interactive forked subagents consistently read files but return planning output — they describe what they *would* do but never execute tool calls.

**Workaround**: Use subagents for read-only scouting/research. Execute all implementation work (file edits, test creation, schema changes) directly in the parent session.

### Subagents in non-interactive mode cannot process intercom replies

When a subagent calls `intercom({ action: "ask", ... })`, the parent session can reply — but the subagent running in **non-interactive** mode will not process the reply. It stays stuck waiting forever (infinite loop).

**Symptoms**: Subagent dispatch runs indefinitely. When you interrupt it, the message says "waiting for response from parent".

**Prevention**: Every subagent definition must use `intercom({ action: "reply", message: "BLOCKED: <reason>" })` instead of `intercom({ action: "ask", ... })` or `contact_supervisor`. The `reply` action is one-shot (fire-and-forget). The parent session inspects the output after the subagent exits.

**If you encounter this bug**: Use `subagent({ action: "interrupt", id: "..." })` to stop the stuck subagent, then fix the agent definition.

### The trilogy must be complete — missing one tool breaks the workflow

- Missing **bash**: Subagent can't run shell commands (common for researcher)
- Missing **intercom reply convention**: Subagent deadlocks on escalation
- Missing **todo tool**: Parent must manually track subagent progress
- Missing **inheritSkills: true**: Subagent can't access project-specific skills

If even one of the four is missing, the subagent workflow will degrade.

### inheritSkills: false is the default — easily missed

Custom subagents (not builtins) default to `inheritSkills: false`. This means they cannot access Pi's discovered skills catalog. **Symptoms of this bug:**

- Subagent produces generic, non-project-specific output
- Subagent fails to follow patterns documented in project skills
- Subagent returns planning text instead of using specialized detection/inspection tools

**Check**: Before every dispatch, verify the agent config includes `inheritSkills: true`. Builtin agents (scout, worker, researcher) also default to `inheritSkills: false` — you must set it explicitly even for builtins.

### Model "works" does not mean tool-calling works

A model that generates good conversational responses may fail at tool-calling. Always test with an actual tool-requiring task:

- **Bad test**: "Analyze this code" — could just return text
- **Good test**: "Run `grep -r 'TODO' app/` and summarize findings" — requires actual bash execution

### Free models expire or change pricing

OpenRouter free tier models frequently change status:
- `inclusionai/ling-2.6-flash:free` → became paid-only
- `baidu/cobuddy:free` → stopped executing tools

Always validate models at the start of a session, especially for long-running projects. As of May 2026, `openrouter/deepseek/deepseek-v4-flash` is a reliable working option for scout/researcher tools.

### Scout output may need human review

Scout tasks return structured reports but may miss nuances. Always review scout findings before acting on them, especially for security audits or architectural decisions.

### Intercom reply vs ask: always use "reply" for non-interactive subagents

- `intercom({ action: "ask", ... })` → subagent blocks waiting for response. **Do not use** in non-interactive worker/scout/researcher agents.
- `intercom({ action: "reply", ... })` → one-shot message to parent. **Use this** in non-interactive agents. Prefix with "BLOCKED:" for escalation semantics.
- `intercom({ action: "send", ... })` → like reply but no expectation of acknowledgment. Use for routine status updates.
## Verification
After dispatching work, verify:

### Subagent succeeded?
- [ ] Output contains actual data (file listings, search results), not planning text
- [ ] Output is not empty or error-only
- [ ] For scouting: report accurately describes the codebase state
- [ ] Subagent followed project-specific patterns (if not, check `inheritSkills: true`)

### Implementation succeeded?
- [ ] Git diff shows actual file changes (not just planning or comments)
- [ ] Tests pass (run `pytest` or equivalent)
- [ ] If graph/task was updated, verify integrity (no orphaned state)

### Model validation passed?
- [ ] Subagent test task produced tool call output (file listings, search hits)
- [ ] Output contains real data, not "I would run..." planning text
- [ ] Task was actually executed (e.g., files exist, grep found matches)

### Config integrity?
- [ ] `inheritSkills: true` is set in the subagent config
- [ ] Shell tools (bash, find, ls, grep) are available for read-based agents
- [ ] Intercom reply convention (BLOCKED: prefix) is in the agent instructions
- [ ] Todo tool is available for self-management