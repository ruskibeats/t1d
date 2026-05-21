---
name: "capture-code-review-failures-as-memories"
description: "Capture bugs and issues found during code review as structured failure memories with category, impact, and concise detail. Use after completing a code review that uncovered multiple actionable bugs — save each bug as a failure memory for cross-session awareness and future diagnostic context."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Capture Code Review Findings as Failure Memories

## When to Use
After completing a code review that uncovered actionable bugs, design issues, or regressions — especially when multiple distinct problems were found. Use this to preserve the findings as durable, categorized failure memories so future sessions benefit from prior diagnostics.

Do NOT use for:
- One-off warnings or linting suggestions
- Hypothetical concerns not confirmed by reading code
- Bugs already captured by a ticketing system (unless the memory adds useful diagnostic detail)

## Procedure

### 1. Collect Findings from the Review
For each distinct issue, extract:
- **What was checked**: the file, feature, or area under review
- **What was found**: the specific bug or issue (method, line, or pattern)
- **Impact**: what would go wrong (silent failure, data loss, wrong output, security)
- **Context**: trigger conditions if non-trivial

### 2. Save Each Bug as a Failure Memory
Use the `memory` tool with `target='failure'` and `category='failure'`. Each bug gets its own entry for independent search and resolution tracking.

```python
memory(
    action="add",
    target="failure",
    category="failure",  # one of: failure, correction, insight, preference, convention, tool-quirk
    failure_reason="Concise statement of what went wrong and why",  # e.g., "dispatch/send doesn't set task.status to 'in_progress'"
    content="Structured description: what was checked → what was found → impact. Keep under 5000 chars."
)
```

**Content format** (concise, structured):
```
[Area/Component]: [specific bug description]
- What: [short description]
- Where: [file/function if known]
- Impact: [concrete consequence]
```

### 3. Handle Memory Size Limits
If any individual memory entry is too large, the save will fail with a size limit error. Follow the **handle-memory-size-limit** skill to replace or remove and retry.

### 4. Verify Persistence
Search for each finding after saving:
```bash
memory_search(query="<keyword from bug>", target="failure", category="failure")
```

## Pitfalls
- **Don't batch bugs into one memory entry** — they become unsearchable independently. Save each bug separately
- **Keep descriptions concise** but specific enough for diagnostic value. The 5000-char limit per entry is generous for individual bugs
- **Failure reason field is optional** but recommended — it becomes the quick-scan summary in search results
- **Don't save code-fix details** in failure memories — save those as skills. The memory captures what was wrong; the skill captures how to fix it
- **Prefer `category='failure'`** for actual bugs. Use `'insight'` for design observations, `'correction'` for user corrections
- **If a bug is project-specific**, also save a project memory in addition to the failure memory:
  ```python
  memory(action="add", target="project", content="...")
  ```

## Verification
1. ✅ Each bug has its own `memory` entry with `target='failure'` and `category='failure'`
2. ✅ Each entry is independently searchable via `memory_search`
3. ✅ Content includes: what was checked, what was found, and impact
4. ✅ No size limit errors during save
5. ✅ Related project-scoped entries also saved if project-specific