/**
 * UpdateMutator — Handles field-wise task mutations.
 *
 * Deepening of state-reducer.ts update action. Encapsulates
 * the repetitive field-by-field update logic.
 */

import type { Task, TaskMutationParams, TaskStatus } from "../tool/types.js";
import { isTransitionValid } from "./transition-validator.js";
import { detectCycle } from "./task-graph.js";
import type { TaskState } from "./state.js";
import { createTaskWithFields } from "./task-factory.js";

/**
 * Create a new task in state.
 */
export function create(state: TaskState, params: TaskMutationParams): {
	state: TaskState;
	task: Task;
} {
	const task = createTaskWithFields({
		item: params.subject ?? params.item ?? "Untitled",
		subject: params.subject,
		description: params.description,
		activeForm: params.activeForm,
		blockedBy: params.blockedBy,
		assigned: params.assigned,
		owner: params.owner,
		tags: params.tags,
		planFile: params.planFile,
		branch: params.branch,
		project: params.project,
		metadata: params.metadata,
	});
	task.id = state.nextId;

	const newTasks = [...state.tasks, task];
	return {
		state: { tasks: newTasks, nextId: state.nextId + 1 },
		task,
	};
}

/**
 * Validates update params before mutation.
 */
export function validateUpdateParams(
	task: Task,
	params: TaskMutationParams,
	state: TaskState,
): { valid: true } | { valid: false; error: string } {
	if (params.id === undefined) {
		return { valid: false, error: "id required for update" };
	}

	if (!params.status && !hasMutableField(params)) {
		return { valid: false, error: "update requires at least one mutable field" };
	}

	if (params.status && !isTransitionValid(task.status, params.status)) {
		return { valid: false, error: `illegal transition ${task.status} → ${params.status}` };
	}

	if (params.addBlockedBy && params.addBlockedBy.length > 0) {
		if (detectCycle(state.tasks, task.id, [...(task.blockedBy ?? []), ...params.addBlockedBy])) {
			return { valid: false, error: "addBlockedBy would create a cycle in the blockedBy graph" };
		}
	}

	if (params.metadata !== undefined) {
		const hasNonNullValue = Object.values(params.metadata).some((v) => v !== null);
		const hasNullValue = Object.values(params.metadata).some((v) => v === null);
		if (!hasNonNullValue && !hasNullValue) {
			// All values are undefined or missing
		}
	}

	return { valid: true };
}

/**
 * Check if params contain at least one mutable field.
 */
function hasMutableField(params: TaskMutationParams): boolean {
	return (
		params.subject !== undefined ||
		params.item !== undefined ||
		params.description !== undefined ||
		params.activeForm !== undefined ||
		params.status !== undefined ||
		params.assigned !== undefined ||
		params.owner !== undefined ||
		params.tags !== undefined ||
		params.planFile !== undefined ||
		params.branch !== undefined ||
		params.project !== undefined ||
		params.metadata !== undefined ||
		(params.addBlockedBy && params.addBlockedBy.length > 0) ||
		(params.removeBlockedBy && params.removeBlockedBy.length > 0)
	);
}

/**
 * Apply a mutation to a task, returning the updated task.
 */
export function mutateTask(task: Task, params: TaskMutationParams): Task {
	let newStatus = task.status;
	if (params.status !== undefined) {
		newStatus = params.status;
	}

	let newBlockedBy = task.blockedBy ? [...task.blockedBy] : [];

	// Remove blockedBy entries
	if (params.removeBlockedBy && params.removeBlockedBy.length > 0) {
		const toRemove = new Set(params.removeBlockedBy);
		newBlockedBy = newBlockedBy.filter((dep) => !toRemove.has(dep));
	}

	// Add blockedBy entries
	if (params.addBlockedBy && params.addBlockedBy.length > 0) {
		for (const dep of params.addBlockedBy) {
			if (dep === task.id) throw new Error(`cannot block #${task.id} on itself`);
			if (!newBlockedBy.includes(dep)) {
				newBlockedBy.push(dep);
			}
		}
	}

	// Merge metadata
	let newMetadata = task.metadata;
	if (params.metadata !== undefined) {
		const merged: Record<string, unknown> = { ...(task.metadata ?? {}) };
		for (const [k, v] of Object.entries(params.metadata)) {
			if (v === null) delete merged[k];
			else merged[k] = v;
		}
		newMetadata = Object.keys(merged).length ? merged : undefined;
	}

	const updated: Task = {
		...task,
		status: newStatus,
		updatedAt: new Date().toISOString(),
	};

	if (params.subject !== undefined) updated.item = params.subject;
	if (params.item !== undefined) updated.item = params.item;
	if (params.description !== undefined) updated.description = params.description;
	if (params.activeForm !== undefined) updated.activeForm = params.activeForm;
	if (params.assigned !== undefined) updated.assigned = params.assigned;
	if (params.owner !== undefined) updated.owner = params.owner;
	if (params.tags !== undefined) updated.tags = params.tags;
	if (params.planFile !== undefined) updated.planFile = params.planFile;
	if (params.branch !== undefined) updated.branch = params.branch;
	if (params.project !== undefined) updated.project = params.project;
	if (newBlockedBy.length) updated.blockedBy = newBlockedBy;
	else delete updated.blockedBy;
	if (newMetadata === undefined) delete updated.metadata;
	else updated.metadata = newMetadata;

	return updated;
}

/**
 * Apply mutation to a state, returning new state.
 */
export function applyMutation(
	state: TaskState,
	params: TaskMutationParams,
): TaskState {
	const idx = state.tasks.findIndex((t) => t.id === params.id);
	if (idx === -1) {
		return state;
	}

	const task = state.tasks[idx];
	const validation = validateUpdateParams(task, params, state);
	if (!validation.valid) {
		return state;
	}

	const updated = mutateTask(task, params);
	const newTasks = [...state.tasks];
	newTasks[idx] = updated;

	return { tasks: newTasks, nextId: state.nextId };
}

/**
 * Update a task by id — wrapper that matches the old API and returns result object.
 */
export function update(state: TaskState, params: TaskMutationParams): {
	state: TaskState;
	task: Task;
	fromStatus: TaskStatus;
	toStatus: TaskStatus;
} {
	const idx = state.tasks.findIndex((t) => t.id === params.id);
	if (idx === -1) {
		throw new Error(`#${params.id} not found`);
	}

	const task = state.tasks[idx];
	const validation = validateUpdateParams(task, params, state);
	if (!validation.valid) {
		throw new Error(validation.error);
	}

	const fromStatus = task.status;
	const updated = mutateTask(task, params);
	const toStatus = updated.status;
	const newTasks = [...state.tasks];
	newTasks[idx] = updated;

	return {
		state: { tasks: newTasks, nextId: state.nextId },
		task: updated,
		fromStatus,
		toStatus,
	};
}