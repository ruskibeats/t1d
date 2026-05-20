/**
 * TaskFactory — Creates new Task instances with defaults.
 *
 * Deepening of state-reducer.ts create action. Centralizes
 * task construction logic so all callers share the same shape.
 */

import type { Task } from "../tool/types.js";

export const EMPTY_STATE_TASK: Task = {
	id: 0,
	item: "",
	status: "pending",
	createdAt: new Date().toISOString(),
	updatedAt: new Date().toISOString(),
};

/**
 * Creates a new Task with minimal fields.
 */
export function createTask(item: string): Task {
	return {
		id: 0, // Will be replaced by store
		item,
		status: "pending",
		createdAt: new Date().toISOString(),
		updatedAt: new Date().toISOString(),
	};
}

/**
 * Creates a new Task with extended fields.
 */
export function createTaskWithFields(fields: {
	item: string;
	subject?: string;
	description?: string;
	activeForm?: string;
	blockedBy?: number[];
	assigned?: string;
	owner?: string;
	tags?: string[];
	planFile?: string;
	branch?: string;
	project?: string;
	metadata?: Record<string, unknown>;
}): Task {
	return {
		id: 0,
		item: fields.item,
		status: "pending",
		createdAt: new Date().toISOString(),
		updatedAt: new Date().toISOString(),
		...(fields.subject ? { subject: fields.subject } : {}),
		...(fields.description ? { description: fields.description } : {}),
		...(fields.activeForm ? { activeForm: fields.activeForm } : {}),
		...(fields.blockedBy && fields.blockedBy.length ? { blockedBy: [...fields.blockedBy] } : {}),
		...(fields.assigned ? { assigned: fields.assigned } : {}),
		...(fields.owner ? { owner: fields.owner } : {}),
		...(fields.tags && fields.tags.length ? { tags: [...fields.tags] } : {}),
		...(fields.planFile ? { planFile: fields.planFile } : {}),
		...(fields.branch ? { branch: fields.branch } : {}),
		...(fields.project ? { project: fields.project } : {}),
		...(fields.metadata ? { metadata: { ...fields.metadata } } : {}),
	};
}

/**
 * Clones a task with a new ID and timestamp.
 */
export function cloneTask(task: Task, id: number): Task {
	return {
		...task,
		id,
		createdAt: new Date().toISOString(),
		updatedAt: new Date().toISOString(),
	};
}

/**
 * Creates a task in a different status (for testing).
 */
export function createTaskWithStatus(
	item: string,
	status: Task["status"],
	id: number,
): Task {
	return {
		id,
		item,
		status,
		createdAt: new Date().toISOString(),
		updatedAt: new Date().toISOString(),
	};
}