---
name: "pi-extension-schema-timestamp-hardening"
description: "Procedure for hardening Pi extension data schemas by adding createdAt and updatedAt timestamps for persistence-aware operations."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use this procedure when developing a Pi extension (or similar state-driven Pi tool) that requires history tracking, reporting, or persistence-aware operations (like generating daily reports, syncing tasks, or audit logs).

## Procedure
1. **Audit Data Schema**: Identify the core `Task` (or entity) type definition file (e.g., `types.ts`).
2. **Define Timestamps**: Add `createdAt` and `updatedAt` fields if they do not exist:
   ```typescript
   createdAt: Type.Number(); // or ISO8601 string depending on persistence
   updatedAt: Type.Number();
   ```
3. **Analyze State Reducer**: Inspect the state reducer (e.g., `state-reducer.ts`) to ensure it properly initializes `createdAt` upon task creation and updates `updatedAt` on *every* mutation.
4. **Enforce Invariants**: If complex transitions are used, update the invariant checker to require or preserve these timestamps.
5. **Verify Persistence**: Check if the persistence layer (e.g., `.pi/todo-state.json`) is reading/writing these fields correctly.

## Pitfalls
- **Reducer Incompleteness**: Forgetting to update `updatedAt` in a specific action handler will cause stale timestamps and break reporting filters.
- **Initialization Errors**: `createdAt` should *never* change after task instantiation.
- **Compiler Exhaustiveness**: Ensure all TypeScript unions/intersections that track the entity are updated.

## Verification
- Create a new task and check the underlying state JSON file for the initialized `createdAt`.
- Mutate an existing task and verify `updatedAt` has updated to the current timestamp.
- Run any report/history tools (like an EOD reporter) to confirm filters work correctly with the new fields.