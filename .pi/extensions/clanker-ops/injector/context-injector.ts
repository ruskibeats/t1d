/**
 * Context Injector — Injects a compact Clanker Ops board summary
 * into the LLM context via system prompt injection.
 *
 * Hooked into session lifecycle events in index.ts so the LLM is
 * always aware of the current work queue without running /clanker.
 */

import { getState } from "../state/store.js";
import { selectTasksByStatus } from "../state/selectors.js";
import { basename } from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// Compact summary (single line for top-of-prompt injection)
// ---------------------------------------------------------------------------

export function formatCompactContext(): string {
	const state = getState();
	const visible = state.tasks.filter((t) => t.status !== "deleted");
	const groups = selectTasksByStatus(state);

	const active = groups.inProgress.slice(0, 3).map((t) => {
		const owner = t.assigned ? `@${t.assigned.replace(/^@/, "")}` : "";
		const plan = planExists(t.id) ? "" : "⚠no-plan";
		return `#${t.id} "${t.item}"${owner}${plan}`;
	});

	const failed = visible.filter((t) => t.status === "failed");
	const blocked = visible.filter((t) => (t.blockedBy?.length ?? 0) > 0);

	const parts: string[] = [];
	parts.push(`${groups.inProgress.length} active`);
	parts.push(`${groups.pending.length} queued`);
	if (failed.length) parts.push(`${failed.length} failed`);
	if (groups.completed.length) parts.push(`${groups.completed.length} done`);

	let compact = `<!-- CLANKER: ${parts.join(", ")}`;
	if (active.length) compact += ` — top: ${active.join("; ")}`;
	if (failed.length) compact += ` — ⚠${failed.length} failed`;
	if (blocked.length) compact += ` — ⊘${blocked.length} blocked`;
	compact += ` -->`;

	return compact;
}

// ---------------------------------------------------------------------------
// Multi-line detail (for session_start full injection)
// ---------------------------------------------------------------------------

export function formatDetailContext(): string {
	const state = getState();
	const visible = state.tasks.filter((t) => t.status !== "deleted");
	const groups = selectTasksByStatus(state);
	const failed = visible.filter((t) => t.status === "failed");
	const blocked = visible.filter((t) => (t.blockedBy?.length ?? 0) > 0);
	const missingPlans = visible.filter(
		(t) => t.status !== "completed" && !planExists(t.id),
	);

	const lines: string[] = ["", "<!-- CLANKER_OPS", `Project: ${basename(process.cwd())}`];

	// Active
	if (groups.inProgress.length) {
		lines.push("", "Active:");
		for (const t of groups.inProgress) {
			const owner = t.assigned ? ` @${t.assigned.replace(/^@/, "")}` : "";
			const plan = planExists(t.id) ? "" : " ⚠no-plan";
			lines.push(`  ◐ #${t.id} ${t.item}${owner}${plan}`);
		}
	}

	// Failed
	if (failed.length) {
		lines.push("", "Failed:");
		for (const t of failed) lines.push(`  ✗ #${t.id} ${t.item}`);
	}

	// Blocked
	if (blocked.length) {
		lines.push("", "Blocked:");
		for (const t of blocked)
			lines.push(`  ⊘ #${t.id} ${t.item} — blockedBy=${(t.blockedBy ?? []).map((d) => `#${d}`).join(",")}`);
	}

	// No-plan
	if (missingPlans.length) {
		lines.push("", "Missing plans:");
		for (const t of missingPlans.slice(0, 5))
			lines.push(`  ⚠ #${t.id} ${t.item}`);
	}

	lines.push("-->");
	return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function planExists(id: number): boolean {
	const planPath = join(process.cwd(), ".pi", "todo-plans", `#${id}_plan.md`);
	return existsSync(planPath);
}