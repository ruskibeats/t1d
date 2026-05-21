---
name: "detect-orphaned-skills"
description: "Detect skill files that exist on disk in .agents/skills/ but are not registered in the lazy-loadable skills-registry.json. Cross-references the filesystem against the registry manifest to find orphaned/unregistered skills, then batch-registers them with appropriate metadata. Use after bulk skill creation, subagent-generated skills, or when auditing skills registry completeness."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Detect and Register Orphaned Skill Files

## When to Use

Use this when:
- You or a subagent created skill files in `.agents/skills/` but forgot to add them to `skills-registry.json`
- You suspect the skills registry is missing entries for skills that exist on disk
- Doing periodic registry hygiene after bulk skill creation or subagent-generated skills
- Onboarding new skills from external sources (e.g., GitHub repos via skills-lock.json)

**Do NOT use for**: Adding a single skill (use `skills-registry-entry-creation` instead), or for creating Pi-native skills via the `skill` tool (those go in `.pi/skills/`, not `.agents/skills/`).

## Procedure

### 1. List all skill files on disk

```bash
cd /root/t1d
find .agents/skills -maxdepth 2 -name "SKILL.md" | sort
```

This shows every skill file directory. Each directory under `.agents/skills/` that contains a `SKILL.md` is a potential skill.

Some directories may be symlinks to archived skills — `find -L` to follow symlinks if needed.

### 2. List all registered skills

```bash
cd /root/t1d
python3 -c "import json; r=json.load(open('.agents/skills-registry.json')); print(*sorted(r['skills'].keys()), sep='\n')"
```

This shows all skills currently registered in the lazy-loadable registry.

### 3. Cross-reference to find orphans

```bash
cd /root/t1d
# Extract skill directory names from disk
find .agents/skills -maxdepth 2 -name "SKILL.md" -not -path "*/skills-archive/*" | sed 's|\.agents/skills/||;s|/SKILL\.md||' | sort > /tmp/disk_skills.txt
# Extract registered skill names
python3 -c "import json; r=json.load(open('.agents/skills-registry.json')); print('\n'.join(sorted(r['skills'].keys())))" | sort > /tmp/registered_skills.txt
# Find orphans
comm -23 /tmp/disk_skills.txt /tmp/registered_skills.txt
```

The `comm -23` output shows skills on disk that are NOT in the registry.

### 4. Read each orphaned skill to determine metadata

For each orphan, read the SKILL.md to understand its purpose:

```bash
read .agents/skills/<name>/SKILL.md
```

Determine:
- **Category**: design, engineering, productivity, utility, misc, personal, image, in-progress
- **Priority**: critical, high, medium, low
- **Size**: small (≤500 tokens), medium (500-1500 tokens), large (1500-2500 tokens)
- **Token estimate**: count or approximate
- **Triggers**: keywords a user would say to invoke this skill
- **Intent patterns**: regex patterns matching user requests

### 5. Batch-register using the existing single-entry procedure

For each orphaned skill, follow `skills-registry-entry-creation`:
1. Create the registry entry in `skills-registry.json` with all required fields
2. Verify the path in `file` points to the correct location
3. Update `lastUpdated` in the registry header

For bulk additions, use `edit` to add multiple entries to the JSON in one call (add them all to the `skills` object at once, keeping alphabetical order).

### 6. Verify

```bash
cd /root/t1d
python3 -c "
import json
r = json.load(open('.agents/skills-registry.json'))
disk = set(
    open('/tmp/disk_skills.txt').read().strip().split('\n')
)
registered = set(r['skills'].keys())
still_missing = disk - registered
if still_missing:
    print(f'STILL MISSING: {still_missing}')
else:
    print('All disk skills are registered. ✓')
"
```

## Pitfalls

1. **Exclude archive/ directories**: The `skills-archive/` subdirectory contains deprecated or restructured skills that intentionally lack registry entries. Exclude these with `-not -path "*/skills-archive/*"` in your find command.

2. **Symlinks can confuse detection**: Some skills may be symlinks to archive directories (e.g., `typescript-expert → skills-archive/typescript-expert`). The find command may or may not follow them depending on the `-L` flag. Be consistent — either always follow symlinks or never.

3. **skills-lock.json entries are NOT registry entries**: The `skills-lock.json` tracks skill sources for reproducibility but is separate from the lazy-loadable registry. A skill can be in skills-lock.json without being in skills-registry.json, and vice versa.

4. **Empty or stub SKILL.md files**: If a SKILL.md file is a one-line stub or TODO placeholder, it doesn't warrant a registry entry. Only register skills with complete, actionable content.

5. **Overly broad triggers**: When adding triggers for batch-registered skills, avoid copy-pasting the same triggers across multiple skills. Each skill should have distinct, targeted trigger keywords.

6. **JSON edit correctness**: When adding entries to `skills-registry.json` in bulk, ensure valid JSON. Each entry must have all 15+ fields (name, title, description, category, subcategory, priority, file, size, tokenEstimate, triggers, intentPatterns, recommended, examples, useWhen, aliases) — the lazy-loader will fail on partial entries.

## Verification

- ✅ Run the cross-reference check from Step 6 — no orphaned skills remain
- ✅ Each newly registered skill has a complete registry entry with all required fields
- ✅ The SKILL.md file at the registered path actually exists and contains substantive content
- ✅ No archive/ or deprecated skills were accidentally registered
- ✅ `lastUpdated` in skills-registry.json reflects the current date
- ✅ Triggers and intent patterns are unique per skill (no two registered skills have identical triggers)