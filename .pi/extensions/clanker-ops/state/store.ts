import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type { Task } from "../tool/types.js";
import { EMPTY_STATE, type TaskState } from "./state.js";

const STATE_PATH = ".pi/todo-state.json";

// ---------------------------------------------------------------------------
// JSON file read/write — .pi/todo-state.json is the single source of truth.
// The module-level state cell from the pre-refactor era is removed entirely.
// ---------------------------------------------------------------------------

function readJsonState(): { items: Task[] } | null {
	if (!existsSync(STATE_PATH)) return null;
	try {
		const raw = readFileSync(STATE_PATH, "utf-8");
		const parsed = JSON.parse(raw) as unknown;
		if (parsed && typeof parsed === "object" && "items" in parsed && Array.isArray((parsed as { items: unknown }).items)) {
			return parsed as { items: Task[] };
		}
		return null;
	} catch {
		return null;
	}
}

function deriveNextId(items: Task[]): number {
	if (items.length === 0) return 1;
	return Math.max(...items.map((t) => t.id)) + 1;
}

function mergeStates(replayed: TaskState, currentItems: Task[]): Task[] {
	const currentMap = new Map(currentItems.map((t) => [t.id, t]));
	const replayedMap = new Map(replayed.tasks.map((t) => [t.id, t]));
	const allIds = new Set([...currentMap.keys(), ...replayedMap.keys()]);
	const merged: Task[] = [];
	for (const id of allIds) {
		const current = currentMap.get(id);
		const replayedTask = replayedMap.get(id);
		if (!current) {
			merged.push(replayedTask!);
		} else if (!replayedTask) {
			merged.push(current);
		} else {
			const currentTime = new Date(current.updatedAt).getTime();
			const replayedTime = new Date(replayedTask.updatedAt).getTime();
			merged.push(replayedTime > currentTime ? replayedTask : current);
		}
	}
	merged.sort((a, b) => a.id - b.id);
	return merged;
}

function toTaskState(items: Task[]): TaskState {
	return { tasks: items.map((t) => ({ ...t })), nextId: deriveNextId(items) };
}

function toJsonPayload(state: TaskState): { items: Task[] } {
	return { items: state.tasks.map((t) => ({ ...t })) };
}

function atomicWrite(path: string, data: string): void {
	const dir = dirname(path);
	if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
	const tempPath = path + ".tmp";
	writeFileSync(tempPath, data, "utf-8");
	renameSync(tempPath, path);
}

// ---------------------------------------------------------------------------
// Public accessors
// ---------------------------------------------------------------------------

export function getTodos(): readonly Task[] {
	return getState().tasks;
}

export function getNextId(): number {
	return getState().nextId;
}

export function getState(): TaskState {
	const json = readJsonState();
	if (json) return toTaskState(json.items);
	return { tasks: [...EMPTY_STATE.tasks], nextId: EMPTY_STATE.nextId };
}

/**
 * Replay seam. Lifecycle handlers in `index.ts` call this on
 * `session_start` / `session_compact` / `session_tree` after
 * `replayFromBranch` decodes the latest snapshot.
 *
 * Merges replayed state with the current JSON file contents using
 * `updatedAt` timestamps to resolve conflicts (e.g. CLI mutations
 * that happened while this Pi session was not running).
 *
 * IMPORTANT: Never overwrite existing JSON with an empty state from replay.
 * This protects against the case where replay finds no tool results but
 * the JSON file has valid data (e.g., from external edits or read failures).
 */
export function replaceState(next: TaskState): void {
	const json = readJsonState();
	if (json && json.items.length > 0) {
		// JSON has valid data - merge with replayed state
		const merged = mergeStates(next, json.items);
		// Strip tombstoned (deleted) items — they exist in the branch replay
		// but should not pollute the persistent state file.
		const clean = merged.filter((t) => t.status !== "deleted");
		commitState({ tasks: clean, nextId: deriveNextId(clean) });
	} else if (json && json.items.length === 0) {
		// JSON exists but is empty - use replayed state only if it has items
		if (next.tasks.length > 0) {
			const clean = next.tasks.filter((t) => t.status !== "deleted");
			commitState({ tasks: clean, nextId: next.nextId });
		}
		// Otherwise keep the empty JSON file as-is (don't write empty state)
	} else {
		// JSON doesn't exist or couldn't be read - use replayed state
		// only if it has actual content (prevents wiping valid data)
		if (next.tasks.length > 0) {
			const clean = next.tasks.filter((t) => t.status !== "deleted");
			commitState({ tasks: clean, nextId: next.nextId });
		}
	}
}

/**
 * Post-reducer commit seam. Tool execute() calls this with the reducer's
 * new state. Writes atomically to `.pi/todo-state.json` so the board
 * renderer and bash CLI always see the latest canonical state.
 */
export function commitState(next: TaskState): void {
	atomicWrite(STATE_PATH, JSON.stringify(toJsonPayload(next), null, 2) + "\n");
}

/**
 * Test-setup reset. Wired into the global `test/setup.ts` `beforeEach`.
 * Clears the JSON file back to empty state.
 */
export function __resetState(): void {
	commitState({ tasks: [...EMPTY_STATE.tasks], nextId: EMPTY_STATE.nextId });
}
