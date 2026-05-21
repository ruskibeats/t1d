---
name: "pi-extension-agent-registry"
description: "Add an agent definition registry to a Pi extension that discovers, parses, and caches markdown agent definitions from `.pi/agents/`. Use when building dispatch, orchestration, or agent-selection features that need to map an owner string (e.g. `@worker`) to a structured agent definition including role, system prompt, and verification steps."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Use when a Pi extension needs to resolve an agent owner string (like `@worker` or `@scout`) into a structured definition containing role context, system prompt, and verification steps. Common triggers:
- Building `/clanker dispatch #N to @worker` where the extension must read `.pi/agents/worker.md`
- Implementing agent-aware orchestration where the extension selects or validates agents
- Any feature that consumes the `.pi/agents/*.md` ecosystem and needs programmatic access

Boundaries:
- Does NOT cover subagent execution or spawning (see `pi-subagents` or `clanker-ops-auto-dispatch`)
- Does NOT cover writing agent definitions (see `clanker-roster-agent-registration`)
- Assumes agent definitions are markdown files with heading-based sections, not strict frontmatter

## Prerequisites

- Agent definition markdown files exist in `.pi/agents/*.md`
- Each file contains at minimum a `## Role` section (first paragraph is the role summary)
- Optional `## Verification` section for post-execution checks
- Node.js `fs` and `path` APIs available in the extension runtime

## Procedure

### Step 1: Define the AgentDefinition Interface

```typescript
export interface AgentDefinition {
  name: string;           // derived from filename (e.g., "worker" from "worker.md")
  role: string;           // first paragraph of ## Role section, or filename fallback
  systemPrompt: string;   // full file content (trimmed), suitable for subagent system prompt
  verification?: string;  // full ## Verification section content, if present
  filePath: string;       // absolute path to the markdown file
}
```

### Step 2: Implement the Markdown Parser

Use regex-based section extraction. Keep it dependency-free:

```typescript
import { readFileSync } from "node:fs";

function parseAgentFile(filePath: string): AgentDefinition | undefined {
  try {
    const content = readFileSync(filePath, "utf-8");
    const basename = filePath.split("/").pop()?.replace(/\.md$/, "") ?? "";
    const name = basename;

    // Extract role: first paragraph under ## Role, stopping at next ## heading or EOF
    const roleMatch = content.match(/^##\s+Role\s*\n([\s\S]*?)(?=\n## |\n*$)/m);
    const role = roleMatch ? roleMatch[1].trim().split('\n')[0] : name;

    // Extract verification section as raw text
    const verificationMatch = content.match(/##\s+Verification[\s\S]*?(?=\n## |\n*$)/);
    const verification = verificationMatch
      ? verificationMatch[0].replace(/^##\s+Verification\s*/, "").trim()
      : undefined;

    return {
      name,
      role,
      systemPrompt: content.trim(),
      verification,
      filePath,
    };
  } catch {
    return undefined;
  }
}
```

### Step 3: Implement Directory Discovery

```typescript
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";

const AGENTS_DIR = join(process.cwd(), ".pi", "agents");

function discoverAgents(): Map<string, AgentDefinition> {
  const agents = new Map<string, AgentDefinition>();
  if (!existsSync(AGENTS_DIR)) return agents;

  for (const entry of readdirSync(AGENTS_DIR, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
    const def = parseAgentFile(join(AGENTS_DIR, entry.name));
    if (def) agents.set(def.name, def);
  }
  return agents;
}
```

### Step 4: Add Lazy Cache with Invalidation

```typescript
let agentCache: Map<string, AgentDefinition> | undefined;

export function resolveAgent(owner: string): AgentDefinition | undefined {
  const cleanName = owner.replace(/^@/, "").trim();
  if (!cleanName) return undefined;

  agentCache ??= discoverAgents();
  return agentCache.get(cleanName);
}

export function invalidateAgentCache(): void {
  agentCache = undefined;
}
```

### Step 5: Wire into Command Handlers

In the extension's dispatch or routing logic:

```typescript
const agent = resolveAgent(task.assigned);
if (!agent) {
  ctx.ui.notify(`Unknown agent: ${task.assigned}. Check .pi/agents/`, "error");
  return;
}

// Use agent.role for task assembly
// Use agent.systemPrompt for subagent system prompt injection
// Use agent.verification for post-run checks
```

## Pitfalls

1. **Regex parsing is brittle.** If agent definitions use non-standard heading levels (e.g., `### Role` instead of `## Role`), the regex fails. Prefer `## Role` as a convention, or make the regex more permissive.
2. **Cache invalidation must be explicit.** The extension has no file watcher on `.pi/agents/`. Call `invalidateAgentCache()` after agent files are created, updated, or deleted.
3. **Owner strings may have `@` prefix.** Always normalize with `.replace(/^@/, "")` before lookup. Store raw strings in task data but normalize at resolution time.
4. **File I/O on every lookup without cache is slow.** In a hot path (e.g., board renderer calling `resolveAgent` per row), the cache prevents reading disk on every call.
5. **Parse failures return `undefined`.** The caller must handle missing agents gracefully — do not assume every owner string maps to a file.
6. **Filenames with dots or spaces.** The `name` is derived from the filename without `.md`. If filenames contain dots, they become part of the name key.

## Verification

1. `resolveAgent("worker")` returns a populated `AgentDefinition` when `.pi/agents/worker.md` exists
2. `resolveAgent("@worker")` returns the **same** definition (normalization works)
3. `resolveAgent("nonexistent")` returns `undefined` (no crash)
4. After adding a new `.pi/agents/tester.md`, `resolveAgent("tester")` finds it without restarting Pi (cache invalidation or lazy discovery works)
5. `agent.role` is the first line of the `## Role` section, not the entire section
6. `agent.verification` contains the full `## Verification` body if present, otherwise `undefined`
7. Board or dispatch commands show meaningful errors for unknown agents instead of silent failures

## References

- Agent definition convention: `.pi/agents/<name>.md` with `## Role` and optional `## Verification`
- Clanker Ops dispatch convention: `clanker-ops-dispatch-convention` skill
- Pi subagent execution: `pi-subagents` skill / `pi-subagents` package internals