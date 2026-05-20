/**
 * todo tool + /clanker command — thin registration shell.
 *
 * Tool/command identity, schema, types, reducer, store, replay, response
 * envelope, selectors, and view formatters live in the layered modules under
 * `tool/`, `state/`, and `view/`. This file is the package-root registration
 * surface — it keeps the tool registration at the package root.
 *
 *
 * Public re-exports below preserve the pre-refactor import surface so that
 * `index.ts`, `todo-overlay.ts`, and the global `test/setup.ts` `beforeEach`
 * continue to import from `./todo.js`.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { loadConfig, validateGuidanceFields } from "./config.js";
import { formatStatusLabel, t } from "./state/i18n-bridge.js";
import { replayFromBranch } from "./state/replay.js";
import { selectTasksByStatus, selectTodoCounts, selectVisibleTasks } from "./state/selectors.js";
import { applyTaskMutation } from "./state/state-reducer.js";
import { commitState, getState, replaceState } from "./state/store.js";
import { buildToolResult } from "./tool/response-envelope.js";
import {
	COMMAND_NAME,
	ERR_REQUIRES_INTERACTIVE,
	MSG_NO_TODOS,
	type TaskMutationParams,
	TOOL_LABEL,
	TOOL_NAME,
	TodoParamsSchema,
	type Task
} from "./tool/types.js";
import { formatCommandTaskLine, renderTodoCall, renderTodoResult } from "./view/format.js";
import { renderClankerBoard } from "./view/board.js";

// English fallbacks for localized /clanker section headers — the box-drawing
// decoration is part of the localized string so translators can adjust spacing.
const SECTION_PENDING = "── Pending ──";
const SECTION_IN_PROGRESS = "── In Progress ──";
const SECTION_COMPLETED = "── Completed ──";

// ---------------------------------------------------------------------------
// Public re-exports — pre-refactor consumers (overlay, tests, index.ts) keep
// importing from `./todo.js`. New code may opt into deeper imports.
// ---------------------------------------------------------------------------

export { isTransitionValid } from "./state/invariants.js";
export { applyTaskMutation } from "./state/state-reducer.js";
export { __resetState, getNextId, getTodos } from "./state/store.js";
export { deriveBlocks, detectCycle } from "./state/task-graph.js";
export type { Task, TaskAction, TaskDetails, TaskStatus } from "./tool/types.js";
export { TOOL_NAME } from "./tool/types.js";

/**
 * Backward-compat replay shim. Pre-refactor `reconstructTodoState(ctx)`
 * mutated module state directly; the new replay seam (`state/replay.ts`)
 * returns a `TaskState` and the caller commits via `replaceState`.
 */
export function reconstructTodoState(ctx: Parameters<typeof replayFromBranch>[0]): void {
	replaceState(replayFromBranch(ctx));
}

// ---------------------------------------------------------------------------
// Tool registration
// ---------------------------------------------------------------------------

export const DEFAULT_PROMPT_SNIPPET = "Manage a task list to track multi-step progress";
export const DEFAULT_PROMPT_GUIDELINES: string[] = [
	"Use `todo` for complex work with 3+ steps, when the user gives you a list of tasks, or immediately after receiving new instructions to capture requirements. Skip it for single trivial tasks and purely conversational requests.",
	"When starting any task, mark it in_progress BEFORE beginning work. Mark it completed IMMEDIATELY when done — never batch completions. Exactly one task should be in_progress at a time.",
	"Never mark a task completed if tests are failing, the implementation is partial, or you hit unresolved errors — keep it in_progress and create a new task for the blocker instead.",
	"Task status is a 4-state machine: pending → in_progress → completed, plus deleted as a tombstone. Pass activeForm (present-continuous label, e.g. 'researching existing tool') when marking in_progress.",
	"Use blockedBy to express dependencies (A is blocked by B). On create, pass blockedBy as the initial set. On update, use addBlockedBy / removeBlockedBy (additive merge — do not resend the full array). Cycles are rejected.",
	"list hides tombstoned (deleted) tasks by default; pass includeDeleted:true to see them. Pass status to filter by a single status.",
	"Subject must be short and imperative (e.g. 'Research existing tool'); description is for long-form detail. activeForm is a present-continuous label shown while in_progress.",
];

export function registerTodoTool(pi: ExtensionAPI): void {
	const guidance = validateGuidanceFields(loadConfig().guidance);
	pi.registerTool({
		name: TOOL_NAME,
		label: TOOL_LABEL,
		description:
			"Manage a task list for tracking multi-step progress. Actions: create (new task), update (change status/fields/dependencies), list (all tasks, optionally filtered by status), get (single task details), delete (tombstone), clear (reset all). Status: pending → in_progress → completed, plus deleted tombstone. Use this to plan and track multi-step work like research, design, and implementation.",
		promptSnippet: guidance.promptSnippet ?? DEFAULT_PROMPT_SNIPPET,
		promptGuidelines: guidance.promptGuidelines ?? DEFAULT_PROMPT_GUIDELINES,
		parameters: TodoParamsSchema,

		async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
			const result = applyTaskMutation(getState(), params.action, params as TaskMutationParams);
			commitState(result.state);
			return buildToolResult(params.action, params as TaskMutationParams, result.state, result.op);
		},

		renderCall(args, theme, _context) {
			return renderTodoCall(args as never, theme, getState());
		},

		renderResult(result, _opts, theme, _context) {
			return renderTodoResult(result, theme);
		},
	});
}

// ---------------------------------------------------------------------------
// /clanker command — Clanker Ops board + subcommands
// ---------------------------------------------------------------------------

const CLANKER_HELP = `╭─── Clanker Ops ───╮
│                    │
│  /clanker         Show work board
│  /clanker help    Show this help
│                    │
╰────────────────────╯`;

const BOARD_HEADER = "╭─── Clanker Ops ───╮";

const BOARD_FOOTER = "╰────────────────────╯";

function renderFallbackBoard(): string {
	const state = getState();
	const visible = selectVisibleTasks(state);
	if (visible.length === 0) return t("command.no_todos", MSG_NO_TODOS);

	const groups = selectTasksByStatus(state);
	const counts = selectTodoCounts(state);

	const lines: string[] = [BOARD_HEADER];
	lines.push(`│ ${counts.completed}/${counts.total} done · ${counts.inProgress} in progress · ${counts.pending} pending`);

	if (groups.pending.length > 0) {
		lines.push("│");
		lines.push(`│ ${t("command.section.pending", SECTION_PENDING)}`);
		for (const task of groups.pending) lines.push(`│  ${formatCommandTaskLine(task, "○")}`);
	}
	if (groups.inProgress.length > 0) {
		lines.push("│");
		lines.push(`│ ${t("command.section.in_progress", SECTION_IN_PROGRESS)}`);
		for (const task of groups.inProgress) lines.push(`│  ${formatCommandTaskLine(task, "◐")}`);
	}
	if (groups.completed.length > 0) {
		lines.push("│");
		lines.push(`│ ${t("command.section.completed", SECTION_COMPLETED)}`);
		for (const task of groups.completed) lines.push(`│  ${formatCommandTaskLine(task, "✓")}`);
	}
	lines.push(BOARD_FOOTER);
	return lines.join("\n");
}

export function registerClankerCommand(pi: ExtensionAPI): void {
	pi.registerCommand(COMMAND_NAME, {
		description: "Clanker Ops — show the work board",
		handler: async (args, ctx) => {
			const input = typeof args === "string" ? args.trim() : "";
			const subcommand = input.split(" ")[0].toLowerCase();

			if (!input) {
				// /clanker (no args) -> show the work board
			} else if (subcommand === "help" || subcommand === "--help" || subcommand === "-h") {
				ctx.ui.notify(CLANKER_HELP, "info");
				return;
			} else if (subcommand === "eod") {
				const now = new Date();
				const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
				const state = getState();
				const completedTasks = state.tasks.filter(
					(t) => t.status === "completed" && new Date(t.updatedAt) > yesterday
				);

				const report = [
					`# Clanker Ops EOD Report - ${now.toLocaleDateString()}`,
					`## Completed Tasks (Last 24h)`,
					...completedTasks.map(t => `- [x] #${t.id} ${t.subject}`),
					completedTasks.length === 0 ? "_No tasks completed in the last 24h._" : ""
				].join("\n");

				ctx.ui.notify(report, "info");
				return;
			} else if (subcommand !== "focus") {
				// INTERCEPTION: Treat unrecognized input as a new work item
				const result = applyTaskMutation(getState(), "create", { subject: input });
				commitState(result.state);
				ctx.ui.notify(`✅ Added: ${input}`, "info");
				// Fall through to show the updated board
			}

			if (!ctx.hasUI) {
				ctx.ui.notify(t("command.requires_interactive", ERR_REQUIRES_INTERACTIVE), "error");
				return;
			}

			// Show the work board (including focus mode)
			let filteredTasks = selectVisibleTasks(getState());
			
			if (subcommand === "focus" && input.split(" ").length > 1) {
				const filter = input.split(" ")[1];
				filteredTasks = selectFilteredTasks(getState(), filter);
			}

			try {
				const board = renderClankerBoard(process.stdout.columns || 120, [...filteredTasks]);
				ctx.ui.notify(board, "info");
			} catch {
				// Fallback to simpler renderer
			}
		},
	});
}
