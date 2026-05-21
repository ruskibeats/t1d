/**
 * background-spawner.ts — Thin facade for background subagent dispatch.
 *
 * Deepening: The inline resolution, config-building, and spawn logic have
 * been extracted into focused modules:
 *   - dispatch/resolver.ts       → Path resolution (jiti CLI, runner script)
 *   - dispatch/config-builder.ts → Config construction + disk write
 *   - dispatch/process-spawner.ts → Process spawn + fallback command
 *
 * This file re-exports the public API surface for backward compatibility
 * and composes the three deepened modules.
 */

import type { DispatchPayload } from "./dispatch.js";
export type { SpawnResult } from "./dispatch/process-spawner.js";
export { executeBackgroundDispatch } from "./dispatch/process-spawner.js";
export { resolveJitiCliPath, resolveRunnerScript } from "./dispatch/resolver.js";
export { buildRunnerConfig, writeConfigToDisk, validateCwd } from "./dispatch/config-builder.js";
