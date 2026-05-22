# Clanker Ops Dispatch — Human Test Guide

## Prerequisites

- Pi session running in `/root/t1d`
- Extension loaded (confirmed by `clanker list` working)
- `pi-subagents` installed (already present at `/root/.pi/agent/npm/node_modules/pi-subagents/`)

---

## Test 1: Basic Dispatch Assembly (No Background Run)

**Goal:** Verify the extension reads the plan, assembles the command, and updates state — without actually firing a subagent.

```bash
# Step 1: Confirm task #11 is in_progress and has an owner
clanker status 11 in_progress
clanker move 11 to @worker

# Step 2: In Pi, dispatch it
/clanker dispatch #11

# Step 3: Verify the output
# You should see:
#   "Dispatched #11 → @worker"
#   Plan path
#   Run ID
#   A ready-to-run subagent command in a code block
```

**Manual checks:**

```bash
# The task should now have dispatch metadata
cat .pi/todo-state.json | jq '.items | map(select(.id == 11)) | .[0] | {status, assigned, metadata}'

# Expected:
# {
#   "status": "in_progress",
#   "assigned": "@worker",
#   "metadata": {
#     "dispatchRunId": "<something>",
#     "dispatchedAt": "2026-...",
#     "dispatchAgent": "worker",
#     "outputPath": "/root/t1d/.pi/todo-plans/dispatch-11-....md"
#   }
# }
```

---

## Test 2: Board Visual Update

**Goal:** Confirm the board renderer shows the dispatched state.

```bash
clanker list
```

Look for line #11. You should see:
- `⇢` icon (instead of `◐`)
- Tags column shows `dispatched`
- `Last` column shows current timestamp

---

## Test 3: Full End-to-End (Background Subagent)

**Goal:** Actually run a background subagent and verify the intercom handler catches completion.

```bash
# Step 1: Reset #11 to pending for a clean test
clanker status 11 pending

# Step 2: In Pi, dispatch it
/clanker dispatch #11

# Step 3: Copy the assembled command from Pi's output. It looks like:
# subagent single --agent worker --async true --output /root/t1d/.pi/todo-plans/dispatch-11-XXXX.md --task "Execute Clanker Ops task #11..."

# Step 4: Paste and run the command in Pi. The subagent will start in background.

# Step 5: The Controller session returns immediately. You can now run:
clanker list
# to see #11 still showing ⇢ (dispatched)

# Step 6: Wait for subagent to complete (or fail), then check:
subagent({ action: "status", runId: "<the-run-id-from-step-2>" })

# Step 7: Check the plan file for Agent Log entries
grep -A 5 "### Agent Log" .pi/todo-plans/#11_plan.md

# Step 8: Check if status auto-updated (intercom event)
cat .pi/todo-state.json | jq '.items | map(select(.id == 11)) | .[0].status'
```

---

## Test 4: Session Restart Recovery

**Goal:** Verify that after a Pi session restart, the extension catches up on background task status.

```bash
# Step 1: Dispatch a task and start a background subagent (Test 3)

# Step 2: Restart Pi session (or start a new one)
# The extension's session_start handler calls pollDispatchArtifacts()

# Step 3: Check board — dispatched tasks should still show correct status
clanker list

# Step 4: Check plan file Agent Log — should have entries from before restart
```

---

## Test 5: Error Handling

**Goal:** Verify graceful failure when prerequisites are missing.

```bash
# Missing plan file
# Create a task with no plan:
clanker add "no-plan task"
# Note the ID (e.g., #133)
clanker move 133 to @worker
# In Pi:
/clanker dispatch #133
# Expected: "Dispatch failed: plan file not found"

# Unknown agent
clanker add "unknown-agent task"
clanker move 134 to @nonexistent
# In Pi:
/clanker dispatch #134
# Expected: "Dispatch failed: unknown agent owner @nonexistent"

# No owner assigned
clanker add "no-owner task"
# In Pi:
/clanker dispatch #<id>
# Expected: "Dispatch failed: task #<id> has no assigned owner"
```

---

## Quick Smoke Test (One-Liner)

```bash
# From terminal, run everything:
clanker status 11 in_progress && \
clanker move 11 to @worker && \
clanker dispatch 11 && \
clanker list | grep "#11"

# Then in Pi:
# /clanker dispatch #11
# Copy the subagent command and run it.
```

---

## Expected Results Summary

| Test | Success Criteria |
|------|-----------------|
| Basic Dispatch | Output shows plan path, runId, and subagent command |
| Board Visual | #11 shows `⇢` icon and `dispatched` tag |
| End-to-End | Subagent runs in background, Agent Log entries appear |
| Session Recovery | After Pi restart, status is correct, no data loss |
| Error Handling | Clear error messages for missing plan, unknown agent, no owner |
