/**
 * Plan Audit — Writes lifecycle event entries to task plan files.
 *
 * Extracted from intercom-handler.ts. Isolates the plan file
 * I/O logic for testability.
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// I/O helpers
// ---------------------------------------------------------------------------

function atomicWrite(path: string, data: string): void {
	writeFileSync(path, data, "utf-8");
}

// ---------------------------------------------------------------------------
// Plan file path resolution
// ---------------------------------------------------------------------------

export function resolvePlanPath(taskId: number): string {
	return join(process.cwd(), ".pi", "todo-plans", `#${taskId}_plan.md`);
}

// ---------------------------------------------------------------------------
// Agent log entry helpers
// ---------------------------------------------------------------------------

export function formatLogEntry(
	emoji: string,
	agent: string,
	message: string,
): string {
	const timestamp = new Date()
		.toISOString()
		.slice(0, 16)
		.replace("T", " ");
	return `- **[${timestamp}]** ${emoji} ${agent}: ${message}`;
}

// ---------------------------------------------------------------------------
// Audit logging
// ---------------------------------------------------------------------------

export interface AuditLogResult {
	success: boolean;
	path?: string;
}

/**
 * Append a log entry to the task's plan file under `### Agent Log`.
 * Creates the section if it doesn't exist.
 */
export function appendAgentLog(taskId: number, entry: string): AuditLogResult {
	const planPath = resolvePlanPath(taskId);
	if (!existsSync(planPath)) {
		return { success: false };
	}

	const content = readFileSync(planPath, "utf-8");
	const agentLogMarker = "### Agent Log";

	if (content.includes(agentLogMarker)) {
		const updated = content.replace(
			agentLogMarker,
			`${agentLogMarker}\n${entry}`,
		);
		atomicWrite(planPath, updated);
	} else {
		atomicWrite(planPath, `${content}\n\n${agentLogMarker}\n${entry}\n`);
	}

	return { success: true, path: planPath };
}

// ---------------------------------------------------------------------------
// Artifact completion check
// ---------------------------------------------------------------------------

export interface ArtifactCheckResult {
	completed: boolean;
	artifact: string;
}

/**
 * Check if a dispatch output artifact indicates completion.
 * Looks for `## Closeout` or `## Audit Report` markers.
 */
export function checkArtifactCompletion(outputPath: string): ArtifactCheckResult | null {
	if (!existsSync(outputPath)) return null;

	const artifact = readFileSync(outputPath, "utf-8");
	const completed =
		artifact.includes("## Closeout") || artifact.includes("## Audit Report");

	return { completed, artifact };
}