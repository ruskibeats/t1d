---
name: clanker-roster-agent-registration
description: Add or update agents in the Clanker Roster document with proper entries, task allocation guidance, and categorization
version: 1
created: 2026-05-19
updated: 2026-05-19
---
## When to Use

Use this when adding a new agent to `docs/CLANKER_ROSTER.md`, updating an existing agent entry, or pruning the roster for the T1D Companion project context. The Clanker Roster catalogs all available agents with their capabilities, optimal use cases, and task allocation guidance.

## Required Roster Sections

The roster document has these sections that must be maintained:

```
# Clanker Roster

---

## Built-in Agents (Default)

For each agent: name, Purpose, Use for, Context mode (if fork), Example usage

---

## Project Agents (T1D-Specific)

For each agent: name, Purpose, Use for, Files (key files it works with)

---

## Engineering Skills (Reusable Procedures)

A curated table: Skill | Purpose | Use Case
With a note about removed skills at the bottom

---

## Design & UI Agents (Curated for T1D)

A curated table: Agent | Purpose | T1D Use Case

---

## Specialized Domain Agents (Curated for T1D)

A curated table: Agent | Purpose | T1D Use Case

---

## Task Allocation Guidelines

Rules for which agent to pick for different task types

---
```

## Procedure

### Adding a New Agent

1. **Read the current roster**: `read docs/CLANKER_ROSTER.md` — understand the existing structure and which section your agent belongs in.

2. **Choose the right section**:
   - **Built-in Agents**: pi-supplied default agents (planner, worker, researcher, reviewer, oracle, delegate, scout, context-builder)
   - **Project Agents**: T1D-specific agents created for implementation phases (phase1-*, phase2-*, fixer-*, reviewer-*)
   - **Engineering Skills**: Reusable procedures like diagnose, tdd, prototype, review, improve-codebase-architecture
   - **Design & UI Agents**: Design-oriented skills curated for T1D (impeccable, design-taste-frontend, minimalist-ui, redesign-existing-projects)
   - **Specialized Domain Agents**: Domain-specific build scripts (build-health-pattern-detection-engine, build-cgm-data-sync-service, etc.)

3. **Format the entry consistently** with the existing agents in that section. Example for Project Agents:
   ```markdown
   ### `agent-name`
   **Purpose:** One-line description of what it does
   **Use for:** When to dispatch this agent
   **Files:** `path/to/key/file.py`
   ```

4. **Update Task Allocation Guidelines** section if the new agent introduces a new task type or category.

### Pruning the Roster

1. **Identify agents to remove**: Agents that are iOS-specific, irrelevant to Python/FastAPI backend, duplicate capabilities, or one-time-use-only.

2. **Remove the entry** from its section.

3. **Update the "Removed" note** at the bottom of the section's table:
   ```markdown
   *(Removed: `agent1`, `agent2`, `agent3` - reason for removal)*
   ```

4. **Verify total count** stays manageable (aim for ~20-35 agents total for T1D context).

### Updating an Existing Agent

1. Change the Purpose, Use for, Files, or Example usage as needed.

2. If the agent's scope has changed substantially, move it to a more appropriate section.

## Verification

- Agent entry follows the same format as surrounding entries in its section
- Agent is placed in the correct section
- No duplicate entries for the same capability
- Task Allocation Guidelines reflect the addition/change
- Total agent count is reasonable for the project scope (target 20-35)
- "Removed" notes at section bottoms are kept up-to-date

## Pitfalls

- **Do NOT add agents that are one-time-use only** (e.g., a single-migration agent). Prefer a generic agent with a specific task.
- **Do NOT include iOS-only agents** (e.g., HealthKit) in the main T1D roster unless iOS is in scope.
- **Do NOT include writing/creative skills** (e.g., writing-beats, obsidian-vault) unless the project requires them.
- **Keep the Purpose line short and specific** — this is the primary field used when choosing an agent from Clanker Ops.
- **Update the Task Allocation Guidelines** when adding a fundamentally new agent type (e.g., domain-specific build agents).
- **Preserve historical "Removed" notes** so it's clear what was intentionally excluded.