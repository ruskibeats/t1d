---
name: "clanker-cli-utility-creation"
description: "Procedure for creating or updating project-specific CLI utilities to manage Clanker Ops tasks using jq."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use when creating or updating project-specific CLI utilities to manage Clanker Ops tasks (using `jq` to manipulate `.pi/todo-state.json`).

## Procedure
1.  **Requirement Analysis**: Define the task lifecycle action needed (e.g., move, change status/data).
2.  **Tooling Selection**: Leverage `jq` for robust JSON manipulation.
3.  **UI Design**: Keep CLI syntax lightweight (e.g., `clanker <action> <args>`).
4.  **Implementation**: Write the bash wrapper handling inputs, validation, and JSON patching using `jq` on `.pi/todo-state.json`.
5.  **Installation**: Place the utility in a directory on the `$PATH` (e.g., `/usr/local/bin/clanker`).
6.  **Verification**: Test actions cover the desired task lifecycle and properly update board state.

## Pitfalls
-   **JSON Errors**: Using non-robust string manipulation instead of `jq`.
-   **State Desync**: Not checking for task ID existence before modifying.
-   **Invalid Paths**: Assuming `todo-state.json` is always in a standard path.

## Verification
Ensure CLI actions modify `.pi/todo-state.json` correctly without corrupting it.