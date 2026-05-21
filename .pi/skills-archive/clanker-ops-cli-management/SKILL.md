---
name: "clanker-ops-cli-management"
description: ""
version: 2
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
When you need to manipulate the Clanker Ops task board state (move, edit, change status, assign), or when implementing or modifying the Pi extension `/clanker` command handler (subcommand routing, intelligent task interception, EOD reporting, focus filtering). Use when working with either the bash `clanker` CLI wrapper or the Pi extension's `registerCommand` handler.
## Procedure
1. **Do NOT use the Pi `todo` tool.** The Clanker Ops board is managed by a standalone CLI wrapper, not the generic Pi `todo` system.
2. **Use the `clanker` wrapper** installed at `/usr/local/bin/clanker`. It is a bash script that acts directly on `STATE_FILE="/root/t1d/.pi/todo-state.json"`.
3. **Supported commands:**
   - `clanker list` — renders the board via `clanker-board` (shows active/queued/done counts)
   - `clanker add "[item name]"` — creates a new task
   - `clanker dispatch <id>` — dispatches a task to a subagent worker
   - `clanker delete <id>` — removes a task
   - `clanker move <id> to @agent` — reassigns a task
   - `clanker eod` — end-of-day workflow
   - `clanker nuke` — destructive reset (use with extreme caution)
4. **Execute via `bash`** (e.g., `bash` with command `clanker move 11 to @builder`). The wrapper uses `jq` for direct JSON edits and a `timestamp()` helper (`date -u +"%Y-%m-%dT%H:%M:%SZ"`) to flag updates.
5. **Dispatching a task to a background worker:**
   a. Run `/clanker dispatch <id>`
   b. Copy the assembled `subagent single --agent worker --async true ...` command from the output
   c. Paste and execute it in Pi to fire the detached background subagent
   d. Note the Run ID from the async confirmation output
   e. Check status once with `subagent action="status" id="<run-id>"` — do not poll in a loop
   f. Update the plan file (`.pi/todo-plans/#<id>_plan.md`) with `dispatchRunId` and output/log paths
   g. Verify the board shows the task as `in_progress` with `dispatchRunId` set

## Pitfalls
- **Using Pi `todo` commands** — `todo action="update"` targets a different state mechanism and will not reflect on the Clanker Ops board.
- **Project scope** — The wrapper is hardcoded to `/root/t1d/.pi/todo-state.json`. It will not work in other project directories without modification.
- **Manual JSON editing** — Avoid editing `.pi/todo-state.json` directly without first verifying structure with `read`; malformed JSON will break the board.
- **Dispatch status bug** — `clanker dispatch` may fail to set `task.status` to `in_progress` and may not update `updatedAt`. Always verify the task state after dispatch and fix with `clanker move` or manual `jq` if needed.
- **Orphan plan files** — `clanker delete` removes the task from state but leaves `.pi/todo-plans/#N_plan.md` on disk. Clean up orphans separately if required.
- **Async run monitoring** — Detached subagent runs should not be polled in busy loops. Check status once, then move on to independent work. Use `subagent action="status"` only when you need the current result, not to wait idly.
- **Copy exact subagent command** — The dispatch output assembles the full `subagent single ...` command with plan path, task text, and output file. Reconstructing it manually risks missing `--async true`, the agent name, or the correct output path.

## Verification
- Run `clanker list` (or `/clanker` board view) to confirm changes are reflected.
- Run `read /usr/local/bin/clanker` to inspect the wrapper script if command behavior is unclear.
- After destructive commands (`delete`, `nuke`), verify task counts in the board header match expectations.
- **After dispatch:**
  - Board shows task as `in_progress` with `dispatchRunId` populated
  - Subagent run status shows `running` or `completed` (not `failed`)
  - Plan file contains `Dispatch Log` section with run ID, output path, and timestamp
  - Output file at `/root/t1d/.pi/todo-plans/dispatch-<id>-<run-id>.md` exists if the run produced output