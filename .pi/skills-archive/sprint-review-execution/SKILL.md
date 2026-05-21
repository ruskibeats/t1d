---
name: sprint-review-execution
description: "Execute sprint review: verify grill-me session outcomes, identify verification gaps, create follow-up tasks for incomplete work, reassign tasks appropriately, and defer orphaned tasks missing plan files. Use when wrapping up a sprint review or grill-me session with actionable follow-ups."
version: 1
created: 2026-05-20
updated: 2026-05-20
---
## When to Use
Use this skill when wrapping up a sprint review, audit, or grill-me session to ensure all verification gaps are addressed and follow-up tasks are created. Specifically:
- After completing a grill-me session
- During sprint wrap-up and handoff
- When verification reveals incomplete work
- When tasks need reassignment after review

## Procedure
1. **Inspect grill-me outputs** for verification gaps and incomplete work items
2. **Check for missing plan files** on active tasks (rule: skip if missing plan files → defer)
3. **Create follow-up tasks** for identified gaps:
   - Frontend validation gaps
   - Orphaned tasks without plans
   - Incomplete sprint items
4. **Reassign tasks** to appropriate agents (@worker, @clanker, @scout)
5. **Defer orphaned tasks** missing required plan files
6. **Mark original review task complete** after all actions taken

## Pitfalls
- Don't create duplicate tasks for work already in progress
- Ensure new tasks have proper plan files before creation
- Verify task ownership matches capability before reassigning
- Handle `todo update` errors gracefully (missing id parameter)

## Verification
- All identified gaps have corresponding follow-up tasks
- Orphaned tasks are marked deferred with explanation
- Sprint review task shows completed status
- New tasks have valid assignees and plan files