/**
 * Dispatch Log — Persistent audit trail for task dispatches.
 *
 * Maintains a structured JSON log at `.pi/dispatch-log.json` recording
 * every dispatch action and its outcome (started, heartbeat, failed, completed).
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { renameSync } from "node:fs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DispatchEntry {
	taskId: number;
	agent: string;
	runId: string;
	status: "dispatched" | "running" | "failed" | "completed";
	startedAt: string;
	completedAt?: string;
	error?: string;
	outputPath?: string;
	pid?: number;
}

export interface DispatchLog {
	entries: DispatchEntry[];
}

// ---------------------------------------------------------------------------
// File path
// ---------------------------------------------------------------------------

const LOG_PATH = join(process.cwd(), ".pi", "dispatch-log.json");

// ---------------------------------------------------------------------------
// Read / Write
// ---------------------------------------------------------------------------

function readLog(): DispatchLog {
	if (!existsSync(LOG_PATH)) return { entries: [] };
	try {
		return JSON.parse(readFileSync(LOG_PATH, "utf-8")) as DispatchLog;
	} catch {
		return { entries: [] };
	}
}

function writeLog(log: DispatchLog): void {
	mkdirSync(dirname(LOG_PATH), { recursive: true });
	const tempPath = LOG_PATH + ".tmp";
	writeFileSync(tempPath, JSON.stringify(log, null, 2) + "\n", "utf-8");
	renameSync(tempPath, LOG_PATH);
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function logDispatch(entry: Omit<DispatchEntry, "startedAt">): void {
	const log = readLog();
	log.entries.push({
		...entry,
		startedAt: new Date().toISOString(),
	});
	writeLog(log);
}

export function logHeartbeat(taskId: number, runId: string): void {
	const log = readLog();
	const entry = log.entries.find(
		(e) => e.taskId === taskId && e.runId === runId,
	);
	if (entry && entry.status === "dispatched") {
		entry.status = "running";
	}
	writeLog(log);
}

export function logCompletion(
	taskId: number,
	runId: string,
	status: "completed" | "failed",
	error?: string,
): void {
	const log = readLog();
	const entry = log.entries.find(
		(e) => e.taskId === taskId && e.runId === runId,
	);
	if (entry) {
		entry.status = status;
		entry.completedAt = new Date().toISOString();
		if (error) entry.error = error;
	}
	writeLog(log);
}

export function logError(
	taskId: number,
	runId: string,
	error: string,
): void {
	logCompletion(taskId, runId, "failed", error);
}

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

export function getDispatchHistory(limit = 20): DispatchEntry[] {
	const log = readLog();
	return log.entries.slice(-limit).reverse();
}

export function getDispatchesForTask(taskId: number): DispatchEntry[] {
	const log = readLog();
	return log.entries
		.filter((e) => e.taskId === taskId)
		.reverse();
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

export function formatDispatchHistory(limit = 20): string {
	const entries = getDispatchHistory(limit);
	if (entries.length === 0) return "No dispatch history yet.";

	const lines: string[] = ["# Dispatch History", ""];
	for (const entry of entries) {
		const statusIcon =
			entry.status === "completed" ? "✅"
			: entry.status === "failed" ? "❌"
			: entry.status === "running" ? "🔄"
			: "📤";
		const time = new Date(entry.startedAt).toLocaleTimeString();
		const duration = entry.completedAt
			? ` (${Math.round((new Date(entry.completedAt).getTime() - new Date(entry.startedAt).getTime()) / 1000)}s)`
			: "";
		lines.push(
			`${statusIcon} #${entry.taskId} → @${entry.agent} [${entry.status}]${duration} ${time}`,
		);
		if (entry.error) lines.push(`   ⚠ ${entry.error}`);
	}

	return lines.join("\n");
}