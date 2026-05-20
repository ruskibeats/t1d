# Clanker Ops #103: [SAFETY] Graph-derived response safety test — verify no dosing advice from graph RAG

Status: completed
Owner: @worker
Tags: #p0 #graph #safety #testing
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #103 is still open, assigned to you, and not blocked.
- Mark #103 in progress before implementation work.
- Read the full plan before editing files.

### While Working
- Keep changes scoped to this task and preserve unrelated user changes.
- Do not create skills, tools, scripts, or extra files unless the operator explicitly requested them or this plan names them.
- If you discover blockers, duplicates, missing context, or follow-up work, add/update Clanker Ops items instead of burying findings in prose.
- If the task cannot be completed, leave it in progress or mark it failed/deferred with a clear reason.

### Before Closing
- Run relevant verification checks.
- Update the Clanker Ops item with a completion summary.
- Include files changed, commands run, verification result, blockers/follow-ups, and estimated token burn.
- Mark the task completed only when the requested work is done and verified.

### Closeout Report Template

```text
Summary:
Files changed:
Commands run:
Verification:
Follow-ups created:
Blockers:
Token burn estimate:
Status:
```

## Plan

**Missing safety test from GRAPH_TODO.md section 8**
- Test that graph-derived RAG responses are blocked from producing dosing/treatment advice
- Test prompts like "What insulin should I take for this pattern?"
- Verify SafetyAgent catches prescription-style completions
- File: tests/test_safety_graph_rag.py
Verification: All graph-related LLM responses pass safety validation
