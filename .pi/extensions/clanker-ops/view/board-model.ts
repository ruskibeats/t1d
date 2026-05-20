/**
 * Board Models - Pure data structures for board rendering.
 *
 * These models transform raw Task data into display-ready structures,
 * separating business logic from ANSI rendering.
 */

import type { Task } from "../tool/types.js";

/**
 * Display model for a single task on the board.
 * Contains pre-computed values for rendering.
 */
export interface BoardTaskViewModel {
	id: number;
	item: string;
	icon: string;
	subjectPaint: string;
	owner: string;
	tags: string;
	planRef: string;
	lastRan: string;
	ownerSpanOnly: boolean;
}

/**
 * Grouped board data for rendering.
 */
export interface BoardViewModel {
	groups: {
		active: readonly BoardTaskViewModel[];
		dontForget: readonly BoardTaskViewModel[];
		queued: readonly BoardTaskViewModel[];
		done: readonly BoardTaskViewModel[];
	};
	counts: {
		total: number;
		pending: number;
		inProgress: number;
		completed: number;
	};
	summary: string;
}

/**
 * Present tasks into a board view model.
 * Pure function - no file I/O, no ANSI codes.
 */
export function presentBoard(tasks: readonly Task[]): BoardViewModel {
	const groups = {
		active: [] as BoardTaskViewModel[],
		dontForget: [] as BoardTaskViewModel[],
		queued: [] as BoardTaskViewModel[],
		done: [] as BoardTaskViewModel[],
	};

	for (const task of tasks) {
		if (task.status === "completed") {
			groups.done.push(toViewModel(task));
		} else if (isDontForget(task)) {
			groups.dontForget.push(toViewModel(task));
		} else if (task.status === "in_progress") {
			groups.active.push(toViewModel(task));
		} else if (task.status === "pending" || task.status === "deferred" || task.status === "failed") {
			groups.queued.push(toViewModel(task));
		}
	}

	const counts = {
		total: groups.active.length + groups.dontForget.length + groups.queued.length + groups.done.length,
		pending: groups.queued.length,
		inProgress: groups.active.length,
		completed: groups.done.length,
	};

	const summaryParts = [];
	if (counts.inProgress > 0) summaryParts.push(`${counts.inProgress} active`);
	summaryParts.push(`${counts.queued} queued`);
	if (counts.failed > 0) summaryParts.push(`${counts.failed} failed`);
	if (summaryParts.length === 0) summaryParts.push("0 queued");

	return {
		groups,
		counts: { ...counts, failed: tasks.filter((t) => t.status === "failed").length, cancelled: tasks.filter((t) => t.status === "cancelled").length },
		summary: summaryParts.join(" · "),
	};
}

function toViewModel(task: Task): BoardTaskViewModel {
	const isFailed = task.status === "failed";
	const isDispatched = task.metadata?.dispatchRunId && task.status === "in_progress";

	let icon = "○";
	if (isFailed) icon = "✗";
	else if (task.status === "in_progress") icon = "◐";
	else if (isDispatched) icon = "⇢";
	else if (isDontForget(task)) icon = "!";

	return {
		id: task.id,
		item: task.item,
		icon,
		subjectPaint: task.status === "failed" || task.status === "cancelled" ? "error" : isDispatched ? "success" : "default",
		owner: task.assigned ?? "",
		tags: (task.tags ?? []).map((t) => `#${t}`).join(" "),
		planRef: planRef(task),
		lastRan: lastRan(task),
		ownerSpanOnly: isOwnerSpan(task.assigned),
	};
}

function isDontForget(task: Task): boolean {
	if (task.status !== "pending" && task.status !== "deferred") return false;
	if (task.assigned) return false;

	const reminderTags = new Set(["remember", "dont-forget", "don't-forget", "chore", "ops", "housekeeping"]);
	const tags = task.tags ?? [];

	return (
		tags.some((tag) => reminderTags.has(tag.toLowerCase())) ||
		/\b(push|commit|git|save memory|checkpoint|deploy|backup|cleanup|document|eod|end of day)\b/.test(task.item.toLowerCase())
	);
}

function planRef(task: Task): string {
	if (!task.id) return "no";
	return task.description?.trim() || "no";
}

function lastRan(task: Task): string {
	const timestamps = [
		task.handoff?.sentAt,
		task.metadata?.dispatchedAt,
		task.status === "completed" ? task.updatedAt : undefined,
	].filter(Boolean) as string[];

	if (timestamps.length === 0) return "-";

	const latest = new Date(Math.max(...timestamps.map((t) => new Date(t).getTime())));
	const today = new Date();

	if (latest.toDateString() === today.toDateString()) {
		return `${String(latest.getHours()).padStart(2, "0")}:${String(latest.getMinutes()).padStart(2, "0")}`;
	}

	return `${String(latest.getMonth() + 1).padStart(2, "0")}-${String(latest.getDate()).padStart(2, "0")}`;
}

function isOwnerSpan(owner?: string): boolean {
	if (!owner) return false;
	return owner === "@dad_웃" || owner === "dad_웃" || owner === "@tom_웃" || owner === "tom_웃";
}