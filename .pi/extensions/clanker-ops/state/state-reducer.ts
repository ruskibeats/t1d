import type { Task, TaskAction, TaskMutationParams, TaskStatus } from "../tool/types.js";
import { isTransitionValid } from "./invariants.js";
import { TransitionValidator } from "./transition-validator.js";
import { TaskFactory } from "./task-factory.js";
import { UpdateMutator } from "./update-mutator.js";
import type { TaskState } from "./state.js";
import { detectCycle } from "./task-graph.js";

/**
 * Reducer outcome. Closed tagged union — adding a new action requires extending
 * this union AND the response-envelope's `formatContent` switch (compiler-
 * enforced exhaustive). Mirrors the `Effect` pattern in
 * Mirrors the Clanker Ops state-reducer pattern.
 *
 * `error` carries the message in-band so callers can pattern-match on
 * `op.kind === "error"` without a side-channel boolean.
 */
export type Op =
	| { kind: "create"; taskId: number }
	| { kind: "update"; id: number; fromStatus: TaskStatus; toStatus: TaskStatus }
	| { kind: "bulk"; count: number; action: string }
	| { kind: "delete"; id: number; subject: string }
	| { kind: "list"; statusFilter?: TaskStatus; includeDeleted: boolean }
	| { kind: "get"; task: Task }
	| { kind: "clear"; count: number }
	| { kind: "error"; message: string };

export interface ApplyResult {
	state: TaskState;
	op: Op;
}

function errorResult(state: TaskState, message: string): ApplyResult {
	return { state, op: { kind: "error", message } };
}

/**
 * Pure reducer: (state, action, params) → (state, op). Mirrors the
 * `applyTaskMutation` of pre-refactor `todo.ts` minus content/details
 * formatting; the response envelope (`tool/response-envelope.ts`) owns
 * formatting, the store (`state/store.ts`) owns commit.
 *
 * Validation is in-line: structural guards (`subject required`, `id required`,
 * `at least one mutable field`) plus state-aware checks (transition legality,
 * dangling/deleted blockedBy, self-block, cycles). Decision: validation stays
 * in-reducer — see Plan §Decisions §Decision 2.
 */
export function applyTaskMutation(state: TaskState, action: TaskAction, params: TaskMutationParams): ApplyResult {
	switch (action) {
		case "create": {
			try {
				const result = UpdateMutator.create(state, params);
				return {
					state: { tasks: result.state.tasks, nextId: result.state.nextId },
					op: { kind: "create", taskId: result.task.id },
				};
			} catch (error) {
				return errorResult(state, (error as Error).message);
			}
		}

		case "update": {
			try {
				const result = UpdateMutator.update(state, params);
				return {
					state: { tasks: result.state.tasks, nextId: result.state.nextId },
					op: { kind: "update", id: result.task.id, fromStatus: result.fromStatus, toStatus: result.toStatus },
				};
			} catch (error) {
				return errorResult(state, (error as Error).message);
			}
		}

		case "list": {
			return {
				state,
				op: {
					kind: "list",
					includeDeleted: params.includeDeleted === true,
					...(params.status !== undefined ? { statusFilter: params.status } : {}),
				},
			};
		}

		case "get": {
			if (params.id === undefined) return errorResult(state, "id required for get");
			const task = state.tasks.find((t) => t.id === params.id);
			if (!task) return errorResult(state, `#${params.id} not found`);
			return { state, op: { kind: "get", task } };
		}

		case "delete": {
			if (params.id === undefined) return errorResult(state, "id required for delete");
			const idx = state.tasks.findIndex((t) => t.id === params.id);
			if (idx === -1) return errorResult(state, `#${params.id} not found`);
			const current = state.tasks[idx];
			if (current.status === "deleted") return errorResult(state, `#${current.id} is already deleted`);
			const updated: Task = { ...current, status: "deleted" };
			const newTasks = [...state.tasks];
			newTasks[idx] = updated;
			return {
				state: { tasks: newTasks, nextId: state.nextId },
				op: { kind: "delete", id: updated.id, subject: updated.item },
			};
		}

		case "bulk": {
			const ids = params.ids as number[] | undefined;
			const bulkAction = params.action as string | undefined;
			if (!ids?.length) return errorResult(state, "ids required for bulk");
			if (!bulkAction && !params.status && !params.assigned && !params.tags) {
				return errorResult(state, "at least one mutation field required for bulk");
			}

			let currentState = state;
			let updatedCount = 0;

			for (const id of ids) {
				const idx = currentState.tasks.findIndex((t) => t.id === id);
				if (idx === -1) continue;

				const subResult = applyTaskMutation(currentState, "update", { ...params, id });
				if (subResult.op.kind !== "error") {
					currentState = subResult.state;
					updatedCount++;
				}
			}

			return {
				state: currentState,
				op: { kind: "bulk", count: updatedCount, action: params.status as string || "update" },
			};
		}
	}
}
