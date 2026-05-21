/**
 * TransitionValidator — Encapsulates valid status transitions.
 *
 * Deepening of state-reducer.ts validation logic. Isolates the
 * VALID_TRANSITIONS table and provides validation helpers.
 */

import type { TaskStatus } from "../tool/types.js";

/**
 * Allowed forward transitions per source status.
 */
export const VALID_TRANSITIONS: Record<TaskStatus, ReadonlySet<TaskStatus>> = {
	"": new Set(["pending", "in_progress", "completed", "deleted", "failed", "cancelled", "deferred"]),
	pending: new Set(["in_progress", "completed", "deleted", "failed", "cancelled", "deferred"]),
	in_progress: new Set(["pending", "completed", "deleted", "failed", "cancelled", "deferred"]),
	completed: new Set(["deleted", "failed", "cancelled"]),
	failed: new Set(["pending", "in_progress", "deleted"]),
	cancelled: new Set(["pending", "in_progress", "deleted"]),
	deferred: new Set(["pending", "in_progress", "deleted"]),
	deleted: new Set(),
};

/**
 * Validates a status transition is legal.
 */
export function isTransitionValid(from: TaskStatus, to: TaskStatus): boolean {
	if (from === to) return true;
	return VALID_TRANSITIONS[from].has(to);
}

/**
 * Returns the set of valid destination statuses for a given source.
 */
export function getValidDestinations(from: TaskStatus): ReadonlySet<TaskStatus> {
	return VALID_TRANSITIONS[from];
}

/**
 * Checks if a transition is reversible (can go back to source).
 */
export function isReversible(from: TaskStatus, to: TaskStatus): boolean {
	if (from === to) return false;
	return VALID_TRANSITIONS[to].has(from);
}

/**
 * All terminal statuses (no further transitions possible).
 */
export const TERMINAL_STATUSES: ReadonlySet<TaskStatus> = new Set(["deleted"]);

/**
 * Check if a status is terminal.
 */
export function isTerminal(status: TaskStatus): boolean {
	return TERMINAL_STATUSES.has(status);
}

/**
 * Get transition description for error messages.
 */
export function getTransitionDescription(from: TaskStatus, to: TaskStatus): string {
	if (from === to) return `already ${to}`;
	return `${from} → ${to}`;
}