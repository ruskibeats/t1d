# Clanker Ops Prompt Pack

Project-scoped prompt guidance for Clanker Ops. These prompts are meant to keep agents consistent when they capture work, write plans, dispatch owners, and close tasks.

Use these prompts as guidance only. Do not create new skills, tools, scripts, or files unless the user explicitly asks for them or the assigned plan requires them.

## Files

- `operator-guide.md` - complete operating rules for Clanker Ops.
- `add-work.md` - turn a user request into a Clanker Ops work item.
- `build-plan.md` - create or improve a task plan file.
- `dispatch.md` - send a task to an owner or subagent.
- `closeout.md` - close a task with summary, verification, and follow-up notes.
- `review-dupes.md` - compare tasks and recommend merge, rename, or keep-separate.
- `review-assigned-plan.md` - review whether a task plan is ready for its assigned clanker.
- `lights-off-eod.md` - end-of-day and shutdown checklist behavior.
- `customize-ui.md` - safe guidance for changing board colors, glyphs, columns, and layout.

## Default Rule

If the user says "add X to Clanker Ops", only add it to the queue with a mini-plan. Do not immediately build X, create a skill, create a tool, or write extra project files unless the user clearly asks for that.
