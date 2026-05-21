/**
 * TaskRepository — Isolates the concern of reading tasks from storage.
 *
 * This is a deepening of the pre-refactor board.ts which embedded
 * file I/O directly in the render function. The repository owns:
 * - Path resolution for the state file
 * - JSON parsing with validation
 * - Interface for testability (can inject mock data)
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { Task } from "../tool/types.js";

const STATE_PATH = ".pi/todo-state.json";

/**
 * Result shape for repository reads. Separates the "found/nothign"
 * concern from the actual data.
 */
export interface TaskRepositoryResult {
	/** Whether the state file existed and was valid JSON */
	found: boolean;
	/** Parsed tasks array, empty if not found */
	items: readonly Task[];
}

/**
 * Reads tasks from the canonical state file. Pure function
 * that can be easily tested with mock data or file fixtures.
 */
export function readTasksFromStateFile(): TaskRepositoryResult {
	const statePath = join(process.cwd(), STATE_PATH);

	if (!existsSync(statePath)) {
		return { found: false, items: [] };
	}

	try {
		const raw = readFileSync(statePath, "utf-8");
		const parsed = JSON.parse(raw) as { items?: unknown };
		if (parsed && Array.isArray(parsed.items)) {
			return { found: true, items: parsed.items as Task[] };
		}
		return { found: false, items: [] };
	} catch {
		return { found: false, items: [] };
	}
}

/**
 * Repository interface for dependency injection.
 * Allows tests to provide mock task data without file I/O.
 */
export interface TaskRepository {
	read(): Promise<readonly Task[]>;
}

/**
 * Production implementation reading from the state file.
 */
export class FileTaskRepository implements TaskRepository {
	async read(): Promise<readonly Task[]> {
		return readTasksFromStateFile().items;
	}
}

/**
 * Test implementation with in-memory task data.
 */
export class MemoryTaskRepository implements TaskRepository {
	constructor(private tasks: readonly Task[] = []) {}

	async read(): Promise<readonly Task[]> {
		return this.tasks;
	}
}

/**
 * Creates the appropriate repository for the current context.
 * During tests, use MemoryTaskRepository; production uses FileTaskRepository.
 */
export function createTaskRepository(tasks?: readonly Task[]): TaskRepository {
	if (tasks !== undefined) {
		return new MemoryTaskRepository(tasks);
	}
	return new FileTaskRepository();
}