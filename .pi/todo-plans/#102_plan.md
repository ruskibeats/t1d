# Clanker Ops #102: [GRAPH] Confidence component/scoring tests — verify decomposed confidence on graph edges

Status: completed
Owner: @worker
Tags: #p1 #backend #graph #testing
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #102 is still open, assigned to you, and not blocked.
- Mark #102 in progress before implementation work.
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

**Missing tests from GRAPH_TODO.md section 8**
- Test `confidence_components` JSON: repetition, temporal_consistency, effect_size, data_completeness, source_quality, recency
- Test confidence thresholds map to language: low="sometimes", medium="has sometimes", high="has often"
- Test confidence_overall computed from weighted components
- File: tests/test_graph_confidence.py
Verification: Confidence tests validate calculation and thresholded language
