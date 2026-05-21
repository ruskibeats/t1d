---
name: "memory-consolidation-hygiene"
description: "Find and consolidate duplicate, outdated, or conflicting memory entries across targets (memory, user, project, failure). Covers searching for duplicates, merging content into a single target, removing stale/outdated entries, handling target validation errors, split-merge for mashup entries, and verifying results. Use when memories have accumulated duplicates, when content exists in multiple targets redundantly, or when doing periodic memory cleanup."
version: 3
created: "2026-05-20"
updated: "2026-05-20"
---
# Memory Consolidation & Hygiene

Systematic procedure for finding and consolidating duplicate, outdated, or conflicting memory entries across the four memory targets (`memory`, `user`, `project`, `failure`).

## When to Use

- Memories have accumulated with duplicate content across multiple targets (e.g., same info in both `memory` and `project`)
- You encounter conflicting or contradictory entries about the same topic
- You've identified stale/outdated entries that supersede older ones
- Doing periodic memory cleanup or pre-session hygiene
- User says "clean up my memories", "deduplicate", or "consolidate memory"
- A single memory entry contains multiple unrelated facts that should be split (mashup entry)

**Do NOT use for**: Single-memory updates, one-off memory adds, or handling specific memory-size-limit errors (use `handle-memory-size-limit` skill instead).

## Procedure

### 1. Survey existing memories

Search broadly across all targets to understand the current state:

```bash
# Search by topic to find duplicates
memory_search(query="<topic>", target="memory")
memory_search(query="<topic>", target="user")
memory_search(query="<topic>", target="project")
memory_search(query="<topic>", target="failure")

# For a full audit, search broadly
memory_search(query=".")
memory_search(query=".", target="failure")
memory_search(query="<project-name>", project="<project-name>")
```

For a thorough audit, also search with empty/near-empty queries to catch entries you might miss:
```bash
memory_search(query=" ", target="user")
memory_search(query=".", target="memory")
```

### 2. Identify duplicates and conflicts

For each topic, flag entries where:

- **Exact duplicates**: Same content stored in multiple targets
- **Near-duplicates**: Same factual content, different wording
- **Conflicting**: Different information about the same topic
- **Superseded**: Older entries that newer ones have replaced
- **Outdated**: No longer relevant (stale dates, completed tasks)
- **Empty**: Entries with blank or placeholder content
- **Mashup entries**: One entry containing multiple unrelated facts that should be separate focused entries

### 3. Plan consolidation

For each group of duplicates/conflicts:

1. Decide the **best single target** for the consolidated entry:
   - `user` → user preferences, identity, communication style
   - `project` → project-specific conventions, paths, decisions
   - `memory` → global/environment facts, tool quirks
   - `failure` → categorized failures, corrections, insights

2. Merge the content, preserving the most accurate/fresh version
3. Add timestamp tags (`<!-- created=YYYY-MM-DD, last=YYYY-MM-DD -->`) so future sessions know recency

For **mashup entries** (one entry with multiple unrelated facts):
1. Identify each distinct fact in the mashup
2. Assign each fact to its correct target (e.g., a user preference and a tool quirk in the same entry)
3. Plan to remove the mashup and create separate focused entries

### 4. Remove stale entries

Use `memory(action="remove", target="<target>", old_text="<unique identifying text>")`.

**Critical rules:**
- `target` must be one of: `"memory"`, `"user"`, `"project"`, `"failure"` — no other values are accepted
- `old_text` must match a substring that uniquely identifies the entry within that target
- If you're unsure whether an entry should be removed, keep it and flag it for review

#### Handling "No entry matched" failures

If `remove` fails with `"No entry matched '...'"`, the `old_text` you provided does not exactly match any entry's text. To recover:

1. **Search for the exact text**: Run `memory_search(query="<key phrase from failed old_text>", target="<target>")` to retrieve the full entry content
2. **Copy the exact text** from the search result — pay attention to leading/trailing whitespace, characters like `—`, `•`, `§`, or special Unicode
3. **Retry the `remove`** with the exact text from the search result
4. **If it still fails**: The entry may have already been removed by a previous step. This is harmless — the entry is already gone. Move on.

**Note on `replace`**: The `memory(action="replace")` operation is **atomic** — it tries to remove the old entry AND add the new content in one step. If the `old_text` doesn't match, **neither** the remove nor the add executes. Prefer separate `remove` + `add` calls for safer error recovery.

### 5. Add consolidated entries

Use `memory(action="add", target="<target>", content="<consolidated content>")`.

For **mashup entries**: After removing the mashup entry, create each focused fact as a separate entry in its appropriate target.

Optionally add `category` for `failure`-target entries (one of: `failure`, `correction`, `insight`, `preference`, `convention`, `tool-quirk`).

### 6. Verify

- Search for the old text to confirm removal
- Search for the new content to confirm addition
- Check that no duplicate remains across targets
- For mashup entries, verify each separate fact exists in its correct target

## Pitfalls

1. **Invalid target values**: The `memory` tool only accepts `target` values of `"memory"`, `"user"`, `"project"`, or `"failure"`. Passing `"global"` will fail with "must be equal to one of the allowed values". Always double-check the target before calling remove/add.

2. **Partial old_text mismatch**: The `old_text` in `remove` must match an entry's text. If only part of the content is provided and it doesn't uniquely match, the remove will fail. Use a sufficiently unique substring. If it fails, search for the exact text and retry (see Procedure §4).

3. **Silent remove failure (entry already removed)**: If an entry was already removed in an earlier step of the same consolidation pass, a subsequent `remove` call for the same entry will fail with "No entry matched '...'". This does **not** mean something is wrong — the entry is already gone. Log the failure and move on; do not re-attempt removal.

4. **Atomic replace failure**: `memory(action="replace")` is atomic. If `old_text` doesn't match, **neither** the remove nor the add execute. Prefer separate `remove` + `add` so you can verify each step and retry independently.

5. **Mashup entries left unsplit**: If one entry contains "User prefers TDD + grill-me skill is in archive + always wait for confirmation", leaving it as one blob hides searchable, reusable information. Always split mashups into separate focused entries per target.

6. **Over-consolidation**: Don't merge entries that should stay separate. A preference about communication style (`user`) and a project convention (`project`) should remain in their respective targets even if about similar topics.

7. **Timestamp overwrite**: When adding consolidated content, include creation and last-used timestamps so future sessions know which content is fresh. Use format: `<!-- created=YYYY-MM-DD, last=YYYY-MM-DD -->`

8. **Race conditions**: If a user adds new memories while you're consolidating, re-verify before removing originals to avoid deleting fresh content. Also, if multiple `remove` calls target the same entry (e.g., from different search queries finding the same entry), subsequent removes will fail harmlessly — this is expected.

9. **Special characters in old_text**: Memory entries often contain Unicode characters (`—`, `•`, `§`, `→`, em-dashes, curly quotes). These must be copied exactly into `old_text`. When searching for text to use in `remove`, copy directly from the search result output to avoid character encoding mismatches.

## Verification

- ✅ Run `memory_search(query="<topic>")` across all four targets — only one consolidated entry remains
- ✅ The consolidated entry contains merged content from all originals
- ✅ No `memory(action="remove")` calls returned validation errors (ignore harmless "already removed" failures)
- ✅ Timestamp tags are present on consolidated entries
- ✅ Empty/outdated entries are removed, not just left as orphans
- ✅ Mashup entries (one entry with multiple unrelated facts) are split into separate focused entries
- ✅ Each separate fact lives in its correct target (`user` vs `memory` vs `project` vs `failure`)