/**
 * Event Types — Lifecycle event classification for subagent dispatch.
 *
 * Extracted from intercom-handler.ts. Defines the canonical event
 * types emitted by pi-subagents and provides a classifier function.
 */

// ---------------------------------------------------------------------------
// Canonical event types
// ---------------------------------------------------------------------------

export const EventType = {
	/** Agent is idle or needs human attention */
	NEEDS_ATTENTION: "needs_attention",
	IDLE: "idle",
	/** Agent has been running for a long time (heartbeat) */
	ACTIVE_LONG_RUNNING: "active_long_running",
	/** Agent completed successfully */
	COMPLETION_GUARD: "completion_guard",
	/** Agent failed */
	FAILED: "failed",
} as const;

export type EventTypeValue = (typeof EventType)[keyof typeof EventType];

// ---------------------------------------------------------------------------
// Raw event shape from pi-subagents
// ---------------------------------------------------------------------------

export interface ControlEventLike {
	agent: string;
	runId: string;
	index?: number;
	"-type"?: string;
	reason?: string;
	message?: string;
}

// ---------------------------------------------------------------------------
// Classified event
// ---------------------------------------------------------------------------

export interface ClassifiedEvent {
	type: EventTypeValue | "unknown";
	taskId: number;
	agent: string;
	message: string;
	runId: string;
}

// ---------------------------------------------------------------------------
// Dispatch state lookup
// ---------------------------------------------------------------------------

import type { Task } from "../tool/types.js";
import { getState } from "../state/store.js";

export function findTaskByRunId(
	runId: string,
): { task: Task; taskId: number } | undefined {
	const state = getState();
	for (const task of state.tasks) {
		const meta = task.metadata as Record<string, unknown> | undefined;
		if (meta && meta.dispatchRunId === runId) {
			return { task, taskId: task.id };
		}
	}
	return undefined;
}

// ---------------------------------------------------------------------------
// Classifier
// ---------------------------------------------------------------------------

export function classifyEvent(
	event: ControlEventLike,
): ClassifiedEvent | null {
	const runId = event.runId;
	if (!runId) return null;

	const found = findTaskByRunId(runId);
	if (!found) return null;

	const type: EventTypeValue | "unknown" =
		(event.type ?? event.reason ?? "unknown") as EventTypeValue | "unknown";

	return {
		type,
		taskId: found.taskId,
		agent: event.agent,
		message: event.message ?? "",
		runId,
	};
}