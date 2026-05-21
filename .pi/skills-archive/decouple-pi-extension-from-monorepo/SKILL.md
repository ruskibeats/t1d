---
name: "decouple-pi-extension-from-monorepo"
description: "Procedure for extracting a Pi extension from a monorepo while retaining necessary functionality."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use when extracting a Pi extension from a monorepo structure (e.g., rpiv-mono) where the code relies on shared, monorepo-managed packages or internal paths that will not exist in the standalone implementation.

## Procedure
1. **Audit Imports**: Perform a full recursive search (rg or find) through all files in the extension folder to identify every import path, especially those pointing to workspaces or internal packages.
2. **Classify Dependencies**:
   - **External**: Third-party packages (e.g., `typebox`). These can be declared in the new extension's `package.json`.
   - **Internal/Shared**: Dependencies on monorepo-specific shared libraries (e.g., `@juicesharp/rpiv-i18n`).
3. **Decouple Internal Dependencies**: For each internal shared library, decide between two strategies:
   - **Standalone Bridge**: Reimplement the minimal necessary surface (e.g., an `i18n-bridge.ts` that just returns hardcoded English strings) to remove the shared workspace dependency.
   - **Externalize**: If the shared library is published to npm, install the actual package instead of relying on the monorepo workspace link.
4. **Resurface Registration**: Ensure `package.json` correctly points to the new standalone entry point (e.g., `./index.ts`) and that the `pi` manifest is valid.
5. **Verify**: Test the registration of slash commands and tools using `pi extension list`. If loading fails, check `package.json` paths and internal import resolution.

## Pitfalls
- **Implicit Dependency Resolution**: The original monorepo might have had complex path mappings (e.g., `tsconfig.json` `paths` or workspace hoists) that the standalone environment lacks.
- **Dependency Bloat**: Avoid naively installing all monorepo packages; prefer standalone implementation bridges for internal utilities.

## Verification
- Confirm that `pi extension list` displays the extension without errors.
- Verify that every tool and slash command registered by the extension is accessible.
- Ensure all previously functional features (e.g., persistent todo overlays, i18n fallbacks) still activate correctly.