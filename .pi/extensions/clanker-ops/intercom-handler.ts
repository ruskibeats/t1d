/**
 * intercom-handler.ts — Thin facade for subagent lifecycle event handling.
 *
 * Deepening: The inline event classification, plan audit logging, and
 * state update logic have been extracted into focused modules:
 *   - intercom/event-types.ts   → Event type constants + classifier
 *   - intercom/plan-audit.ts    → Plan file audit trail logging
 *   - intercom/state-updater.ts → State mutations + artifact polling
 *
 * This file re-exports the public API surface for backward compatibility.
 */

import type { ControlEventLike } from "./intercom/event-types.js";
export { handleIntercomEvent, pollDispatchArtifacts } from "./intercom/state-updater.js";
export type { ControlEventLike } from "./intercom/event-types.js";
