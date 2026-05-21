---
name: "handle-memory-size-limit"
description: "Resolve 'Memory at X chars. Adding this entry (...) would exceed the limit' errors from the memory tool. Use when a memory save fails with a size limit error — replace or remove existing entries then retry."
version: 5
created: "2026-05-20"
updated: "2026-05-20"
---
# Handle Memory Tool Size Limit Errors

## When to Use
The `memory` tool returns an error like:
```
Memory at 5233/5000 chars. Adding this entry (...) would exceed the limit. Replace or remove existing entries first.
```
Use this procedure whenever a memory save fails due to the 5000-char per-entry limit. This is a hard constraint — you must reduce the targeted entry's size or free space by removing stale content.

## Procedure
### 1. Diagnose the Error
The error message tells you:
- Current entry size (e.g., `5233/5000 chars`)
- New content would exceed the limit
- The fix: Replace or remove existing entries first

**Do not retry with `action='add'`** — it will fail again.

### 2. Find the Entry to Modify
```bash
# Search for the specific entry by topic
memory_search(query="<topic>", target="<target>")
```
Use `target` matching what you were saving to: `"user"`, `"memory"`, or `"failure"`.
**Do NOT use `"project"` as a target value** — `memory_search` only accepts `"memory"`, `"user"`, or `"failure"`.
To search project-scoped memories, use the separate `project` parameter:
```
memory_search(query="<topic>", project="<project-name>", target="failure")
```

### 3. Choose Your Strategy (fallback chain)

#### Strategy A: Replace (preserve the entry, update content)
Use when the entry has grown large with accumulated content that can be summarized more concisely.
```python
memory(
    action="replace",
    target="<same target>",
    old_text="unique substring identifying the entry to replace",
    content="concise new content (under 5000 chars)"
)
```
**`old_text`**: A substring that uniquely identifies the existing entry. It's matched against the text of existing entries of that `target`.

**If `replace` fails with "No entry matched"**:
The `old_text` substring doesn't match any stored entry's text exactly. Use `memory_search` with relevant keywords to find the entry first, then copy a distinctive phrase from the search result as your `old_text`.

**If `replace` also fails with a size error**, the consolidated content is still too large. Move to Strategy B.

#### Strategy B: Remove stale entries first, then add
Use when old entries can be deleted to free space, or when Strategy A failed.
```python
memory(
    action="remove",
    target="<same target>",
    old_text="unique substring identifying the entry to remove"
)
```
Then retry the original `action="add"` call.

### 4. Retry the Save
After the replace/remove succeeds, retry your original `action="add"` call. It should now succeed.
## Pitfalls
- **`action='add'` will fail again** after a size error. It is not retryable — you must `replace` or `remove` first
- **`old_text` is a substring match**, not a full text. Use a distinctive phrase from the entry (e.g., a date, a unique keyword). If it matches multiple entries, the first match will be replaced/removed
- **Size limit is per entry, not total across all targets**. `user`, `memory`, `project`, and `failure` each have their own 5000-char limit
- **The error message encourages two options but doesn't say how**: `replace` action uses `old_text` to identify the target; `remove` action also uses `old_text`
- **Cannot append to an entry that's at the limit**. If the entry is already 5000 chars, `add` will fail. Use `replace` with consolidated content
- **`replace` can ALSO fail with a size error** if your consolidated content is still too large (e.g., replacement would put memory at 6279/5000). When this happens, you must switch to Strategy B: `remove` one or more stale entries first to free space, then use `action='add'` with the new content
- **Memory Search is your finder**: Use `memory_search` to locate the entry's key text before attempting replace/remove
- **`memory_search` target parameter only accepts `"memory"`, `"user"`, or `"failure"`**: Passing `target="project"` will trigger a validation error (`must be equal to one of the allowed values`). To scope by project, use the separate `project` parameter instead (e.g., `memory_search(query="...", project="t1d", target="failure")`)
- **"No entry matched" on replace**: If `memory(action="replace")` returns "No entry matched", the `old_text` substring doesn't match any stored content. Don't guess — use `memory_search` to locate the exact text first, then choose a distinctive phrase from the search result. Common causes: typos, whitespace differences, or the entry living under a different target than expected
## Verification
1. ✅ The `replace` or `remove` call returns `success: true`
2. ✅ The subsequent `add` call returns `success: true`
3. ✅ New content is searchable via `memory_search` with relevant keywords