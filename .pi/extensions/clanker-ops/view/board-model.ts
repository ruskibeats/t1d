/**
 * Board Models — Pure data structures and classification for board rendering.
 *
 * Separates business logic from ANSI rendering. All functions are pure
 * (no file I/O, no side effects) and fully testable.
 */

import { visualWidth } from "./text-utils.js";
import type { Task } from "../tool/types.js";

// ---------------------------------------------------------------------------
// Text normalization (for duplicate detection)
// ---------------------------------------------------------------------------

export function normText(value: string): string {
	return String(value || "")
		.toLowerCase()
		.replace(/\[[^\]]+\]/g, " ")
		.replace(/#[\w-]+/g, " ")
		.replace(/[^\w\s]/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}

// ---------------------------------------------------------------------------
// Classification helpers
// ---------------------------------------------------------------------------

const REMINDER_TAGS = new Set([
	"remember",
	"dont-forget",
	"don't-forget",
	"chore",
	"ops",
	"housekeeping",
]);

const DONT_FORGET_KEYWORDS =
	/\b(push|commit|git|save memory|checkpoint|deploy|backup|cleanup|document|eod|end of day)\b/;

export function isDontForget(task: Task): boolean {
	if (task.status !== "pending" && task.status !== "deferred") return false;
	if (task.assigned) return false;

	const tags = task.tags ?? [];
	return (
		tags.some((tag) => REMINDER_TAGS.has(tag.toLowerCase())) ||
		DONT_FORGET_KEYWORDS.test(task.item.toLowerCase())
	);
}

export function isDuplicate(task: Task, all: readonly Task[]): boolean {
	const subject = normText(task.item);
	if (!subject) return false;

	return all.some((other) => {
		if (other.id === task.id || other.status === "completed") return false;
		const otherSubject = normText(other.item);
		return (
			otherSubject !== "" &&
			(subject === otherSubject ||
				subject.includes(otherSubject) ||
				otherSubject.includes(subject))
		);
	});
}

// ---------------------------------------------------------------------------
// Priority colors
// ---------------------------------------------------------------------------

export type PriorityLevel = "p0" | "p1" | "p2" | "none";

export function getPriorityLevel(task: Task): PriorityLevel {
	const tags = task.tags ?? [];
	const lowered = tags.map((t) => t.toLowerCase());
	if (lowered.includes("p0")) return "p0";
	if (lowered.includes("p1")) return "p1";
	if (lowered.includes("p2")) return "p2";
	return "none";
}

// ---------------------------------------------------------------------------
// Visual classification
// ---------------------------------------------------------------------------

export interface VisualStyle {
	icon: string;
	paint: "red" | "orange" | "amber" | "green" | "cyan" | "purple" | "gray" | "default";
	priorityLevel: PriorityLevel;
}

export function classifyVisual(
	task: Task,
	all: readonly Task[],
): VisualStyle {
	const isFailed = task.status === "failed" || task.metadata?.lastAlert?.startsWith("needs_attention");
	const longRunning = task.metadata?.lastAlert?.startsWith("long_running");
	const blocked = (task.blockedBy?.length ?? 0) > 0;
	const duplicate = isDuplicate(task, all);
	const dispatched = !!task.metadata?.dispatchRunId && task.status === "in_progress";
	const sent = task.handoff?.status === "sent";
	const dontForget = isDontForget(task);

	let icon = "○";
	if (isFailed) icon = "✗";
	else if (longRunning && !isFailed) icon = "⏱";
	else if (dontForget) icon = "!";
	else if (dispatched) icon = "⇢";
	else if (sent) icon = "⇢";
	else if (blocked) icon = "⊘";
	else if (duplicate) icon = "⧉";
	else if (task.status === "cancelled") icon = "×";
	else if (task.status === "deferred") icon = "◌";
	else if (task.status === "in_progress") icon = "◐";

	let paint: VisualStyle["paint"] = "default";
	if (isFailed) paint = "red";
	else if (dontForget) paint = "amber";
	else if (blocked) paint = "cyan";
	else if (dispatched || sent) paint = "green";
	else if (duplicate) paint = "purple";

	return {
		icon,
		paint,
		priorityLevel: getPriorityLevel(task),
	};
}

// ---------------------------------------------------------------------------
// Tag formatting
// ---------------------------------------------------------------------------

export function formatTags(task: Task): string {
	return (task.tags ?? []).map((tag) => `#${tag}`).join(" ");
}

// ---------------------------------------------------------------------------
// Plan reference
// ---------------------------------------------------------------------------

export function classifyPlanRef(task: Task): "exists" | "missing" | "none" {
	if (!task.id) return "none";
	if (task.status === "completed") return "exists";
	if (task.description?.trim()) return "exists";
	return "missing";
}

// ---------------------------------------------------------------------------
// Activity timestamp
// ---------------------------------------------------------------------------

export function getLatestActivity(task: Task): Date | undefined {
	const meta = task.metadata as Record<string, unknown> | undefined;
	const stamps: Array<string | undefined> = [
		task.handoff?.sentAt,
		task.planHandoff?.sentAt,
		meta?.dispatchedAt as string | undefined,
	];
	if (task.status === "completed" && task.updatedAt) stamps.push(task.updatedAt);

	const dates = stamps
		.filter(Boolean)
		.map((v) => new Date(v!))
		.filter((d) => !Number.isNaN(d.getTime()))
		.sort((a, b) => b.getTime() - a.getTime());

	return dates[0];
}

export function formatLastRan(task: Task): string {
	const date = getLatestActivity(task);
	if (!date) return "-";

	const today = new Date();
	if (date.toDateString() === today.toDateString()) {
		return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
	}
	return `${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// Owner classification
// ---------------------------------------------------------------------------

export function isOwnerSpan(owner?: string): boolean {
	if (!owner) return false;
	return (
		owner === "@dad_웃" ||
		owner === "dad_웃" ||
		owner === "@tom_웃" ||
		owner === "tom_웃"
	);
}

// ---------------------------------------------------------------------------
// Board view model
// ---------------------------------------------------------------------------

export interface BoardTaskViewModel {
	id: number;
	item: string;
	icon: string;
	paint: VisualStyle["paint"];
	priorityLevel: PriorityLevel;
	owner: string;
	ownerSpanOnly: boolean;
	tags: string;
	planRef: "exists" | "missing" | "none";
	lastRan: string;
	status: Task["status"];
}

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
		failed: number;
		cancelled: number;
		completed: number;
	};
	summary: string;
}

export function presentBoard(tasks: readonly Task[]): BoardViewModel {
	const groups = {
		active: [] as BoardTaskViewModel[],
		dontForget: [] as BoardTaskViewModel[],
		queued: [] as BoardTaskViewModel[],
		done: [] as BoardTaskViewModel[],
	};

	const { failed, cancelled } = countByStatus(tasks);

	for (const task of tasks) {
		if (isDontForget(task)) {
			groups.dontForget.push(toViewModel(task, tasks));
		} else if (task.status === "in_progress") {
			groups.active.push(toViewModel(task, tasks));
		} else if (task.status === "completed") {
			groups.done.push(toViewModel(task, tasks));
		} else {
			groups.queued.push(toViewModel(task, tasks));
		}
	}

	const total =
		groups.active.length +
		groups.dontForget.length +
		groups.queued.length +
		groups.done.length;

	const summaryParts: string[] = [];
	if (groups.active.length > 0) summaryParts.push(`${groups.active.length} active`);
	summaryParts.push(`${groups.queued.length + groups.dontForget.length} queued`);
	if (failed > 0) summaryParts.push(`${failed} failed`);
	if (cancelled > 0) summaryParts.push(`${cancelled} cancelled`);
	summaryParts.push(`${groups.done.length} done`);

	return {
		groups,
		counts: {
			total,
			pending: groups.queued.length,
			inProgress: groups.active.length,
			failed,
			cancelled,
			completed: groups.done.length,
		},
		summary: summaryParts.join(" · "),
	};
}

function countByStatus(tasks: readonly Task[]) {
	let failed = 0;
	let cancelled = 0;
	for (const t of tasks) {
		if (t.status === "failed") failed++;
		if (t.status === "cancelled") cancelled++;
	}
	return { failed, cancelled };
}

function toViewModel(task: Task, all: readonly Task[]): BoardTaskViewModel {
	const visual = classifyVisual(task, all);
	return {
		id: task.id,
		item: task.item,
		icon: visual.icon,
		paint: visual.paint,
		priorityLevel: visual.priorityLevel,
		owner: task.assigned ?? "",
		ownerSpanOnly: isOwnerSpan(task.assigned),
		tags: formatTags(task),
		planRef: classifyPlanRef(task),
		lastRan: formatLastRan(task),
		status: task.status,
	};
}

// ---------------------------------------------------------------------------
// Task ranking for "top open work"
// ---------------------------------------------------------------------------

export function rankTask(task: Task): number {
	const tags = task.tags ?? [];
	const lowered = tags.map((t) => t.toLowerCase());

	if (task.status === "failed") return 0;
	if ((task.blockedBy?.length ?? 0) > 0) return 1;
	if (lowered.includes("p0")) return 2;
	if (lowered.includes("p1")) return 3;
	if (lowered.includes("p2")) return 4;
	return 5;
}

// ---------------------------------------------------------------------------
// Column widths
// ---------------------------------------------------------------------------

export interface ColumnWidths {
	icon: number;
	id: number;
	work: number;
	owner: number;
	tags: number;
	plan: number;
	last: number;
}

export function computeColumnWidths(innerWidth: number): ColumnWidths {
	const fixed = 2 + 5 + 13 + 24 + 14 + 7 + 9; // col widths + 8 spacing + 1 right margin
	return {
		icon: 2,
		id: 5,
		work: Math.max(24, innerWidth - fixed),
		owner: 13,
		tags: 24,
		plan: 14,
		last: 7,
	};
}

// ---------------------------------------------------------------------------
// Layout helper
// ---------------------------------------------------------------------------

export function computeLayout(innerWidth: number, title: string, summary: string): string {
	const gap = Math.max(1, innerWidth - title.length - summary.length);
	return `${title}${" ".repeat(gap)}${summary}`;
}