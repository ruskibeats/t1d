---
name: "clanker-ops-plan-bulk-update"
description: "Apply consistent structural updates (rename sections, add new required sections, update template content) across many existing .pi/todo-plans/#N_plan.md files simultaneously. Covers finding all plan files, checking which need updates, applying changes via sed/scripts, and verifying with grep counts. Use when standardizing plan templates across the task board or adding a new required section to all plans."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Use this when you need to apply a consistent structural change across many existing `.pi/todo-plans/#N_plan.md` files simultaneously, such as:

- Adding a new required section (e.g., "Execution Protocol", "Closeout Report Template") to all plans
- Renaming sections or rebranding (e.g., "Todo #N: " → "Clanker Ops #N: ")
- Updating a template section that exists in all plans (e.g., adding the `tokens` field to the Audit/EOD Report-Back section)
- Standardizing plan file structure after a refactor

**This is NOT for writing a single new plan file** — use `clanker-ops-plan-write` for that.

**Trigger phrases**: "update all plan files", "add section to all plans", "bulk update plan templates", "standardize plan files", "rename across all plans", "batch update todos"

## Procedure

### Step 1: Find all plan files and inspect current state

```bash
# List all plan files with count
ls .pi/todo-plans/*_plan.md | wc -l

# Check which files already have (or lack) the target section
grep -c "## Execution Protocol" .pi/todo-plans/*_plan.md

# Check which files have an old section name that needs replacing
grep -c "^# Todo " .pi/todo-plans/*_plan.md

# Check which files already have the new section (to avoid double-insertion)
grep -c "^# Clanker Ops " .pi/todo-plans/*_plan.md
```

**Count results pattern**: `grep -c` prints `filename:N` for each file. Count zeroes (`:0`) means the file lacks the section. Non-zero means it has it.

### Step 2: Identify the exact scope of changes

Determine what changes each file needs. There are three common patterns:

**Pattern A — Simple rename across all files** (e.g., replace "# Todo #N:" with "# Clanker Ops #N:")
```bash
# Preview the change with sed (dry run with output to stdout)
sed -n 's/^# Todo /# Clanker Ops /p' .pi/todo-plans/*_plan.md

# Apply with sed -i
sed -i 's/^# Todo /# Clanker Ops /' .pi/todo-plans/*_plan.md
```

**Pattern B — Insert a new section into all files** (e.g., add "## Execution Protocol" after the header block, before "## Plan")

For this, you need to know the insertion point in each file. Common anchor patterns:
- Before `## Plan` (if present)
- After the header block (Status/Owner/Tags/Branch lines)
- Before `## Intended Outcome` (for the old-style plan structure)

Use `awk` or `sed` with a range pattern to insert after/before specific lines:

```bash
# Example: insert "## Execution Protocol" block before "## Plan" in all files
for f in .pi/todo-plans/*_plan.md; do
    if grep -q "^## Plan" "$f" && ! grep -q "^## Execution Protocol" "$f"; then
        sed -i '/^## Plan/i\
## Execution Protocol\n\
\
### Before Starting\n\
- Run `clanker-board --context-only` from the project root to load current queue context.\n\
- Confirm #N is still open, assigned to you, and not blocked.\n\
- Mark #N in progress before implementation work.\n\
- Read the full plan before editing files.\n\
\
### While Working\n\
- Keep changes scoped to this task.\n\
- If you discover blockers, duplicates, or follow-up work, add/update Clanker Ops items.\n\
- If the task cannot be completed, leave it in progress or mark it failed/deferred with a clear reason.\n\
\
### Before Closing\n\
- Run relevant verification checks.\n\
- Update the Clanker Ops item with a completion summary.\n\
- Mark the task completed only when the requested work is done and verified.\n\
' "$f"
    fi
done
```

**Pattern C — Add a field to an existing section across all files** (e.g., add `- **Tokens consumed**: approximate total` to every Audit section)

```bash
# Example: add tokens field to existing Audit (EOD Report-Back) section
for f in .pi/todo-plans/*_plan.md; do
    if grep -q "^## Audit" "$f" && ! grep -q "Tokens consumed" "$f"; then
        # Find the Audit section and add the tokens line after "Completed by the agent"
        sed -i '/^Completed by the agent.*/a\
- **Tokens consumed**: approximate total' "$f"
    fi
done
```

### Step 3: Verify the changes

```bash
# Count how many files now have the new section
grep -c "## Execution Protocol" .pi/todo-plans/*_plan.md | grep -c ":1"

# Check for outliers — files that still lack the section
grep -c "## Execution Protocol" .pi/todo-plans/*_plan.md | grep ":0$"

# Spot-check a few files to verify content is correct
head -20 .pi/todo-plans/#1_plan.md
head -20 .pi/todo-plans/#85_plan.md  # newer tasks should also be covered

# Confirm total file count is consistent
echo "Total plan files: $(ls .pi/todo-plans/*_plan.md | wc -l)"
echo "Files with new section: $(grep -l '## Execution Protocol' .pi/todo-plans/*_plan.md | wc -l)"
```

The two counts should match. If they don't, the missing files need manual attention.

### Step 4: Handle outliers manually

Some plan files may have unique structures that don't match the bulk pattern:
- Stub plans (just a header, no sections) — may need full rewrite via `clanker-ops-plan-write`
- Non-standard ordering (custom sections between header and ## Plan)
- Already-completed files with different template versions

For these outliers, read the file and apply targeted edits:

```bash
# List the outliers
grep -c "## Execution Protocol" .pi/todo-plans/*_plan.md | grep ":0$"

# Read an outlier
cat .pi/todo-plans/#23_plan.md | head -30

# Apply a targeted edit
# ... manual fix per file
```

## Pitfalls

### Double-insertion is the most common mistake
Always check whether a file already has the section before inserting. Use `grep -q` as a guard check in your loop. Without the guard, you'll duplicate the section on re-runs.

### Different plan file structures may require different insertion points
Not all plan files follow the exact same template. Some have:
- `## Plan` (newer task format)
- `## Intended Outcome` as first section (old format)
- No recognizable sections yet (stub)
- Additional custom sections (e.g., "## Design Notes", "## Research Findings")

Inspect 2-3 representative files before writing the bulk update script, especially if the codebase has evolved across template versions.

### sed -i has different syntax on macOS (BSD) vs Linux (GNU)
On macOS: `sed -i '' 's/foo/bar/' file` (requires empty string argument)
On Linux: `sed -i 's/foo/bar/' file` (no argument)
This project runs on Linux, so use the Linux syntax. If portability is needed, use `sed -i.bak` to create backups.

### `grep -c` with `:0` filter finds missing files
The pattern `grep -c "SECTION" *.md | grep ":0$"` finds files that lack the section. Always run this after the bulk update to catch outliers.

### Back up state before bulk operations
```bash
cp .pi/todo-plans/ .pi/todo-plans.bak -r
```
This lets you snapshot-and-restore if the bulk update goes wrong (wrong insertion point, corrupted sections).

### For loops with sed -i can corrupt files if the script has errors
Test your sed/awk script on 2-3 files first before running on all files. Use a dry-run approach:
```bash
# Dry run: show what would change without modifying files
for f in .pi/todo-plans/#1_plan.md .pi/todo-plans/#2_plan.md; do
    echo "=== $f ==="
    sed 's/^# Todo /# Clanker Ops /' "$f"
done | less
```

### `grep -q` vs `grep -c` for guards
Use `grep -q` (quiet, exit code only) in if-statements within loops — it's faster than `grep -c` and works as a truthy/falsy check:
```bash
if grep -q "## Execution Protocol" "$f"; then
    echo "File $f already has section, skipping"
fi
```

### Plan files for tasks that were already completed before the template change may have outdated sections
Don't force-update completed files unless the task explicitly requires it. If the update is cosmetic (renaming), it's safe to update all. If it's structural (adding new requirements), consider whether applying to completed tasks is meaningful.

## Verification

- [ ] Total file count unchanged: `ls .pi/todo-plans/*_plan.md | wc -l` is the same before and after
- [ ] All files have the new section: `grep -c "NEW_SECTION" .pi/todo-plans/*_plan.md | grep ":0$"` returns empty
- [ ] No double-insertions: spot-check 3-5 files to confirm the section appears exactly once
- [ ] Content is correct: read 2-3 representative files to verify the inserted content matches expectations
- [ ] Plan-specific values (Status, Owner, Tags) are preserved and not corrupted
- [ ] Task ID in the header (e.g., "# Clanker Ops #1:") is correct and not duplicated
- [ ] Original header lines (Status, Owner, Tags, Branch) are intact
- [ ] Git diff of the operation is clean (no weird artifacts, no binary diffs)