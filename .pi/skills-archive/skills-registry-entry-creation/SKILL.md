---
name: skills-registry-entry-creation
description: Add a new skill to the lazy-loadable skills registry with all required metadata for agent matching
version: 1
created: 2026-05-19
updated: 2026-05-19
---
## When to Use

Use this when adding a new skill to the T1D Companion project's lazy-loadable skills system. The skills registry lives at `.agents/skills-registry.json` and skill content files go in `.agents/skills/skills-archive/<skill-name>/SKILL.md`. Unlike the `skill` tool (which saves Pi-native skills to the agent's global/project memory area), this procedure registers skills in the project's own lazy-loadable skills framework.

## The Registry Entry Structure

Each skill in `skills-registry.json` has this shape:

```json
"skill-name": {
  "name": "skill-name",
  "title": "Human-Readable Title",
  "description": "One-paragraph summary of what the skill does and when to use it.",
  "category": "design|engineering|productivity|misc|personal|utility|in-progress|image",
  "subcategory": "Specific sub-category",
  "priority": "critical|high|medium|low",
  "file": "skills-archive/skill-name/SKILL.md",
  "size": "small|medium|large",
  "tokenEstimate": 400-2000,
  "triggers": ["keyword1", "keyword2", "phrase with spaces"],
  "intentPatterns": ["regex.*pattern", ".*for.*matching.*"],
  "recommended": true|false,
  "examples": ["Example usage 1", "Example usage 2"],
  "useWhen": "Brief guidance on when to trigger this skill",
  "aliases": ["alt-name1", "alt-name2"]
}
```

## Procedure

1. **Read the current registry**: `read .agents/skills-registry.json` to understand existing entries and category conventions.

2. **Choose the right category**:
   - `design`: UI polish, aesthetics, style systems, brand systems, image generation
   - `engineering`: Architecture, testing, debugging, prototyping, workflow
   - `productivity`: Handoff, skill creation, communication, context management
   - `utility`: Output control, maintenance, tooling
   - `misc`: Git safety, scaffolding, pre-commit setup, migration
   - `personal`: Writing, note-taking, article editing

3. **Set priority appropriately**:
   - `critical`: Always-consider skills (full-output-enforcement, minimalist-ui)
   - `high`: Important but not essential (impeccable, diagnose, tdd)
   - `medium`: Standard tools (brandkit, triage, grill-with-docs)
   - `low`: Specialized/niche tools (gpt-taste, scaffold-exercises, migrate-to-shoehorn)

4. **Write trigger keywords**:
   - Include both single words and short phrases
   - Cover multiple phrasings of the same intent
   - Prefer terms a user would naturally say (e.g. "polish this UI" not "enhance user interface rendering")
   - 6-15 triggers per skill

5. **Write intent patterns** (regex):
   - Cover the trigger keywords and common phrasings
   - Use `.*` for flexible matching
   - Example: `["review.*ui", "polish.*design", "improve.*interface"]`

6. **Estimate token size**:
   - `small` (≤500 tokens): Compact utility skills
   - `medium` (500-1500 tokens): Standard skills with examples
   - `large` (1500-2500 tokens): Comprehensive skills with multiple sections

7. **Write the skill content file**: Create `.agents/skills/skills-archive/<name>/SKILL.md` with the full skill instructions. The SKILL.md should follow the same pattern as existing skills (markdown with When to Use, Procedure, Verification, Pitfalls sections).

8. **Add the entry to the registry**: Use `edit` to insert the new skill entry into the `skills` object of `.agents/skills-registry.json`. Place it in alphabetical order near related skills.

9. **Update `lastUpdated`** in the registry to the current date (YYYY-MM-DD format).

## Verification

- The new entry is present in `.agents/skills-registry.json` under `skills`
- All 15+ fields are present (name, title, description, category, subcategory, priority, file, size, tokenEstimate, triggers, intentPatterns, recommended, examples, useWhen, aliases)
- The corresponding SKILL.md file exists at the path specified in `file`
- `lastUpdated` reflects the current date
- Triggers and intentPatterns cover the skill's use cases
- Priority is appropriate for the skill's importance to the project

## Pitfalls

- **Do NOT add sk**ils to the registry without creating the corresponding SKILL.md file first — the lazy-loader will fail when trying to load them.
- **Do NOT use overly broad triggers** (e.g., "code" or "design") that would cause false-positive matches.
- **Do NOT use overly narrow triggers** that make the skill hard to match.
- **Keep tokenEstimate accurate** — the lazy-loader uses this for context window budgeting.
- **Set `recommended` to `false`** for niche or infrequently-used skills so they don't clutter the default load set.
- **Follow alphabetical ordering** for the skills entries in the JSON — it makes it easier to spot duplicates and find entries.
- **For engineering skills**, use the path prefix `skills-archive/engineering/<name>/SKILL.md` to match the existing convention.