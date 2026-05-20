/**
 * State Updater — Maps intercom events to task state mutations.
 *
 * Extracted from intercom-handler.ts. Each event type maps
 * to a specific state update strategy.
 */

import { existsSync } from "node:fs";
import { applyTaskMutation } from "../state/state-reducer.js";
import { commitState, getState } from "../state/store.js";
import {
	appendAgentLog,
	checkArtifactCompletion,
	formatLogEntry,
} from "./plan-audit.js";
import type { ClassifiedEvent } from "./event-types.js";
import { classifyEvent, type ControlEventLike } from "./event-types.js";
import { logCompletion, logHeartbeat } from "../dispatch/dispatch-log.js";

// ---------------------------------------------------------------------------
// State update per event type
// ---------------------------------------------------------------------------

/** Handlers for each event type */
type UpdateHandler = (event: ClassifiedEvent) => void;

const handlers: Record<string, UpdateHandler> = {
	needs_attention: handleNeedsAttention,
	idle: handleNeedsAttention,
	active_long_running: handleActiveLongRunning,
	completion_guard: handleFailed,
	failed: handleFailed,
};

function handleNeedsAttention(event: ClassifiedEvent): void {
	const logEntry = formatLogEntry(
		"⚠️",
		event.agent,
		`needs attention: ${event.message || "no activity observed"}`,
	);
	appendAgentLog(event.taskId, logEntry);
	logHeartbeat(event.taskId, event.runId);

	const alertResult = applyTaskMutation(getState(), "update", {
		id: event.taskId,
		metadata: { lastAlert: `needs_attention: ${event.message}` },
	});
	commitState(alertResult.state);
}

function handleActiveLongRunning(event: ClassifiedEvent): void {
	const logEntry = formatLogEntry(
		"⏱️",
		event.agent,
		`heartbeat: ${event.message || "running"}`,
	);
	appendAgentLog(event.taskId, logEntry);

	const longResult = applyTaskMutation(getState(), "update", {
		id: event.taskId,
		metadata: {
			lastAlert: `long_running: ${event.message}`,
			lastHeartbeat: new Date().toISOString(),
		},
	});
	commitState(longResult.state);
}

function handleFailed(event: ClassifiedEvent): void {
	const logEntry = formatLogEntry(
		"❌",
		event.agent,
		`failed: ${event.message}`,
	);
	appendAgentLog(event.taskId, logEntry);
	logCompletion(event.taskId, event.runId, "failed", event.message);

	const failResult = applyTaskMutation(getState(), "update", {
		id: event.taskId,
		status: "failed" as const,
		metadata: {
			lastAlert: `failed: ${event.message}`,
			completedAt: new Date().toISOString(),
		},
	});
	commitState(failResult.state);
}

function handleUnknown(event: ClassifiedEvent): void {
	const logEntry = formatLogEntry(
		"ℹ️",
		event.agent,
		`event (${event.type}): ${event.message}`,
	);
	appendAgentLog(event.taskId, logEntry);
}

// ---------------------------------------------------------------------------
// Public dispatch
// ---------------------------------------------------------------------------

/**
 * Apply an intercom event to task state.
 * Logs to plan file and updates task metadata/status.
 */
export function applyEventToState(event: ClassifiedEvent): void {
	const handler = handlers[event.type];
	if (handler) {
		handler(event);
	} else {
		handleUnknown(event);
	}
}

// ---------------------------------------------------------------------------
// Top-level composition — classify + apply
// ---------------------------------------------------------------------------

/**
 * Handle an intercom event from pi-subagents.
 * Classifies the event and applies it to task state.
 */
export function handleIntercomEvent(event: ControlEventLike): void {
	const classified = classifyEvent(event);
	if (!classified) return; // Event not tracked — ignore
	applyEventToState(classified);
}

// ---------------------------------------------------------------------------
// Artifact polling — catch up on missed intercom events after restart
// ---------------------------------------------------------------------------

/**
 * Poll dispatch output files for completion status.
 * Called on session start to catch up on missed intercom events.
 */
export function pollDispatchArtifacts(): void {
	const state = getState();
	for (const task of state.tasks) {
		if (task.status !== "in_progress" || !task.metadata) continue;

		const meta = task.metadata as Record<string, unknown>;
		const outputPath = meta.outputPath as string | undefined;
		const runId = meta.dispatchRunId as string | undefined;

		if (!outputPath || !runId) continue;

		const result = checkArtifactCompletion(outputPath);
		if (!result) continue;
		if (!result.completed) continue;

		const pidInfo = meta.pid ? ` PID-${meta.pid}` : "";
		const logEntry = formatLogEntry("✅", "dispatch", `COMPLETED${pidInfo} — Output: ${outputPath}`);
		appendAgentLog(task.id, logEntry);

		const completeResult = applyTaskMutation(getState(), "update", {
			id: task.id,
			status: "completed" as const,
			metadata: {
				completedAt: new Date().toISOString(),
				lastAlert: undefined,
			},
		});
		commitState(completeResult.state);
	}
}