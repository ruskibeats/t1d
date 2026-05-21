---
name: "clanker-plan-path-troubleshooting"
description: "Troubleshoot missing or mismatched Clanker Ops plan files (.pi/todo-plans/) and verify file paths."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use this procedure when facing issues with Clanker Ops plan files (e.g., file not found, command execution error referencing a plan file, or board hygiene audits of the `.pi/todo-plans/` directory).

## Procedure
1. **Identify the Task ID**: Confirm the Clanker Ops task ID (e.g., `#11`).
2. **Examine Directory**: List the contents of the plan directory to locate valid files:
   `ls -F .pi/todo-plans/`
3. **Regex Search**: If the file list is dense, use `grep` to find the exact filename:
   `ls -F .pi/todo-plans/ | grep "#11"`
4. **Verify Path**: Ensure the file path used in commands matches the exact output from the directory listing. Pay attention to case-sensitivity and characters like `#`.
5. **Validate Contents**: Read the plan file to confirm it meets the mandatory sections criteria (Intended Outcome, Step-by-Step, Verification, Dependencies, Audit).

## Pitfalls
- **Typo in Path**: Manually typing `#11_plan.md` can lead to errors if the actual file is named `#11_plan.md` vs `11_plan.md`. Always rely on `ls` output.
- **Missing File**: If the file does not exist, do not attempt to read/edit it. Escalate to creating the required plan file based on task specifications.
- **Stale Listings**: If recently created, ensure the filesystem sync has occurred before assuming the file is truly absent.

## Verification
- File path exists in the file system output.
- File contents contain required sections as defined in Clanker Ops guidelines.