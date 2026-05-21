import type { TaskStatus } from "../tool/types.js";

/**
 * Allowed forward transitions per source status. `completed` is one-way to
 * `deleted` (never back to `in_progress`); `deleted` is terminal.
 *
 * Idempotent same→same is checked separately in `isTransitionValid` so this
 * table only enumerates actual transitions.
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

export function isTransitionValid(from: TaskStatus, to: TaskStatus): boolean {
	if (from === to) return true;
	return VALID_TRANSITIONS[from].has(to);
}
