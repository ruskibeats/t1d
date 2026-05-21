---
name: "refactor-to-standalone-pi-extension"
description: "Standalone Pi Extension Pattern: Refactoring monorepo packages into independent, self-contained, zero-dependency Pi extensions."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use when refactoring a Pi extension that depends on external monorepo packages (e.g., `rpiv-mono`, shared SDKs) into a standalone, shareable, production-grade extension.

## Procedure
1. **Analyze Dependencies**: Use `grep` or `rg` to find imports pointing to monorepo/external packages.
2. **Retrieve Source**: Download/copy the required source files from the external repository directly into the extension's local directory.
3. **Decouple**:
   - Create a local, thin `i18n-bridge.ts` that provides English fallbacks instead of depending on a full i18n SDK.
   - Replace dynamic imports (`import('@org/package')`) with direct local imports.
   - Update `package.json` to remove external dependencies.
4. **Rename/Rebrand**: Update tool names, command names (`/command`), and UI branding to match the project's domain (e.g., `rpiv-todo` -> `clanker-ops`).
5. **Reconcile Drifts**: Ensure the fix is applied across all extension installations (both project-level `.pi/extensions/` and profile-level `~/.pi/agent-profiles/.../.pi/extensions/`).
6. **Verify Clean**: Ensure no dangling `node_modules` or `package-lock.json` lockfile refs to the old monorepo remain.

## Pitfalls
- **Ignoring Profile-level Copies**: Pi environments often have cached/profile-specific versions of extensions that must be manually synchronized.
- **Dangling Dependencies**: Leaving old dependencies in `package.json` even after replacing the code can cause install failures.
- **Hard-coded naming**: Failing to completely swap names (tool IDs, config keys, locale namespaces) results in UI/TUI conflicts.

## Verification
- Run the command (e.g., `/clanker`) in the TUI.
- Check that the extension registers tools/commands without errors.
- Verify `index.ts` loads correctly without unresolved imports.