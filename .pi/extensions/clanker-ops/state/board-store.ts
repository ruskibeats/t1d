/**
 * Board-aware state store - supports multiple task board files
 *
 * Each board is a separate JSON file in .pi/boards/ directory.
 * Currently active board determines which tasks are visible.
 */

import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, basename } from "node:path";
import type { Task } from "../tool/types.js";
import { EMPTY_STATE, type TaskState } from "../state/state.js";

const BOARDS_DIR = ".pi/boards";

// ---------------------------------------------------------------------------
// Board file discovery
// ---------------------------------------------------------------------------

export interface BoardInfo {
	name: string;
	path: string;
	taskCount: number;
}

export function listBoards(): BoardInfo[] {
	// Check for legacy default board
	const boards: BoardInfo[] = [];
	
	// Check default .pi/todo-state.json
	if (existsSync(".pi/todo-state.json")) {
		try {
			const raw = readFileSync(".pi/todo-state.json", "utf-8");
			const parsed = JSON.parse(raw) as { items?: Task[] };
			const count = parsed?.items?.length ?? 0;
			boards.push({ name: "main", path: ".pi/todo-state.json", taskCount: count });
		} catch {
			boards.push({ name: "main", path: ".pi/todo-state.json", taskCount: 0 });
		}
	}
	
	// Check .pi/boards directory
	if (existsSync(BOARDS_DIR)) {
		const entries = require("node:fs").readdirSync(BOARDS_DIR);
		for (const entry of entries) {
			if (entry.endsWith(".json")) {
				const path = `${BOARDS_DIR}/${entry}`;
				const name = entry.replace(".json", "");
				try {
					const raw = readFileSync(path, "utf-8");
					const parsed = JSON.parse(raw) as { items?: Task[] };
					const count = parsed?.items?.length ?? 0;
					boards.push({ name, path, taskCount: count });
				} catch {
					boards.push({ name, path, taskCount: 0 });
				}
			}
		}
	}
	
	return boards;
}

// ---------------------------------------------------------------------------
// Board state operations
// ---------------------------------------------------------------------------

let activeBoardPath = ".pi/todo-state.json";

export function getActiveBoardPath(): string {
	return activeBoardPath;
}

export function setActiveBoard(path: string): void {
	if (path === "main") {
		activeBoardPath = ".pi/todo-state.json";
	} else if (path.endsWith(".json")) {
		activeBoardPath = path;
	} else {
		activeBoardPath = path.startsWith(BOARDS_DIR) ? path : `${BOARDS_DIR}/${path}.json`;
	}
}

export function getBoardName(path: string): string {
	if (path === ".pi/todo-state.json") return "main";
	return basename(path, ".json");
}

// ---------------------------------------------------------------------------
// Board JSON operations
// ---------------------------------------------------------------------------

function readBoardState(path: string): TaskState | null {
	try {
		if (!existsSync(path)) return null;
		const raw = readFileSync(path, "utf-8");
		const parsed = JSON.parse(raw) as unknown;
		if (parsed && typeof parsed === "object" && "items" in parsed) {
			const items = (parsed as { items: Task[] }).items || [];
			return { tasks: items, nextId: items.reduce((m, t) => Math.max(m, t.id), 0) + 1 };
		}
		return null;
	} catch {
		return null;
	}
}

function writeBoardState(path: string, state: TaskState): void {
	const dir = dirname(path);
	if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
	const payload = JSON.stringify({ items: state.tasks }, null, 2);
	const tempPath = path + ".tmp";
	writeFileSync(tempPath, payload + "\n");
	renameSync(tempPath, path);
}

// ---------------------------------------------------------------------------
// Public state API
// ---------------------------------------------------------------------------

export function getBoardState(): TaskState {
	const state = readBoardState(activeBoardPath);
	if (state) return state;
	return { tasks: [...EMPTY_STATE.tasks], nextId: EMPTY_STATE.nextId };
}

export function commitBoardState(state: TaskState): void {
	writeBoardState(activeBoardPath, state);
}

// Legacy compatibility - these delegate to active board
export function getState(): TaskState {
	return getBoardState();
}

export function commitState(state: TaskState): void {
	commitBoardState(state);
}

// ---------------------------------------------------------------------------
// Board creation
// ---------------------------------------------------------------------------

export function createBoard(name: string): BoardInfo {
	const path = name === "main" ? ".pi/todo-state.json" : `${BOARDS_DIR}/${name}.json`;
	writeBoardState(path, { tasks: [], nextId: 1 });
	return { name, path, taskCount: 0 };
}