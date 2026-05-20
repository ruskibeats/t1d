/**
 * Command Router — Routes /clanker commands to handlers.
 *
 * Extracted from todo.ts to separate routing logic from tool registration.
 * Each subcommand handler receives shared context (state, notifications)
 * and returns whether the board should be refreshed.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { getState } from "../state/store.js";
import { applyTaskMutation } from "../state/state-reducer.js";
import { commitState } from "../state/store.js";
import { selectVisibleTasks, selectFilteredTasks } from "../state/selectors.js";
import { renderClankerBoard } from "../view/board.js";
import { t } from "../state/i18n-bridge.js";
import { ERR_REQUIRES_INTERACTIVE, COMMAND_NAME } from "../tool/types.js";
import { assembleDispatch } from "../dispatch.js";

// ---------------------------------------------------------------------------
// Handler type
// ---------------------------------------------------------------------------

export interface CommandContext {
	input: string;
	subcommand: string;
	notify: (msg: string, level: string) => void;
	hasUI: boolean;
}

type Handler = (ctx: CommandContext) => Promise<boolean>;

// ---------------------------------------------------------------------------
// Built-in subcommands
// ---------------------------------------------------------------------------

const CLANKER_HELP = `╭─── Clanker Ops ───╮
│                    │
│  /clanker         Show work board
│  /clanker help    Show this help
│  /clanker dispatch #<id> [to <owner>]
│  /clanker eod     End-of-day report
│  /clanker focus   Filtered board view
│  /clanker <text>  Add new work item
│                    │
╰────────────────────╯`;

const BOARD_HEADER = "╭─── Clanker Ops ───╮";
const BOARD_FOOTER = "╰────────────────────╯";

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

const handlers: Record<string, Handler> = {
	help: handleHelp,
	"--help": handleHelp,
	"-h": handleHelp,
	eod: handleEod,
	dispatch: handleDispatch,
	focus: handleFocus,
};

/** No subcommand — show board */
async function handleEmpty(ctx: CommandContext): Promise<boolean> {
	ctx.notify(renderClankerBoard(120, null, null, true), "info");
	return false;
}

/** Help text */
async function handleHelp(ctx: CommandContext): Promise<boolean> {
	ctx.notify(CLANKER_HELP, "info");
	return false;
}

/** End-of-day report */
async function handleEod(ctx: CommandContext): Promise<boolean> {
	const now = new Date();
	const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
	const state = getState();
	const completedTasks = state.tasks.filter(
		(t) => t.status === "completed" && new Date(t.updatedAt) > yesterday,
	);

	const report = [
		`# Clanker Ops EOD Report — ${now.toLocaleDateString()}`,
		"",
		"## Completed Tasks (Last 24h)",
		...completedTasks.map((t) => `- [x] #${t.id} ${t.item}`),
		completedTasks.length === 0 ? "_No tasks completed in the last 24h._" : "",
	].join("\n");

	ctx.notify(report, "info");
	return false;
}

/** Dispatch a task to an agent */
async function handleDispatch(ctx: CommandContext): Promise<boolean> {
	const parts = ctx.input.split(" ");
	const taskId = parseInt(parts[1]?.replace("#", ""));
	const owner = parts.length > 3 && parts[2] === "to" ? parts[3] : undefined;

	if (!taskId || Number.isNaN(taskId)) {
		ctx.notify("Usage: /clanker dispatch #<id> [to <owner>]", "error");
		return false;
	}

	if (owner) {
		const assignResult = applyTaskMutation(getState(), "update", {
			id: taskId,
			assigned: owner,
		});
		commitState(assignResult.state);
	}

	const payload = assembleDispatch(taskId);
	if (!payload) {
		ctx.notify(
			`Dispatch failed: task #${taskId} not ready (missing plan, owner, or agent definition).`,
			"error",
		);
		return false;
	}

	// Auto-spawn
	let spawnResult:
		| { autoSpawned: boolean; error?: string; fallbackCommand?: string }
		| undefined;
	try {
		const { executeBackgroundDispatch } = await import("../background-spawner.js");
		spawnResult = executeBackgroundDispatch(payload);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		spawnResult = { autoSpawned: false, error: message };
	}

	// Update task metadata
	const metaResult = applyTaskMutation(getState(), "update", {
		id: taskId,
		status: "in_progress",
		metadata: {
			dispatchRunId: payload.runId,
			dispatchedAt: new Date().toISOString(),
			dispatchAgent: payload.agent,
			outputPath: payload.outputPath,
			...(spawnResult?.autoSpawned ? { autoSpawned: true } : {}),
		},
	});
	commitState(metaResult.state);

	const msgLines: string[] = [
		`### Dispatched #${taskId} → @${payload.agent}`,
		"",
		`**Plan:** ${payload.planPath}`,
		`**Run ID:** ${payload.runId}`,
	];

	if (spawnResult?.autoSpawned) {
		msgLines.push("", "🔥 **Auto-fired in background** — no manual step needed.");
		msgLines.push("Check status with:");
		msgLines.push("```bash");
		msgLines.push(`subagent({ action: "status", id: "${payload.runId}" })`);
		msgLines.push("```");
	} else {
		msgLines.push("", "**Execute this command to start background work:**");
		msgLines.push("```bash");
		msgLines.push(
			`subagent single --agent ${payload.agent} --async true --output ${payload.outputPath} --task "${payload.task.replace(/"/g, '\\"')}"`,
		);
		msgLines.push("```");
		msgLines.push("", "The subagent will run in the background. Check status with:");
		msgLines.push("```bash");
		msgLines.push(`subagent({ action: "status", id: "${payload.runId}" })`);
		msgLines.push("```");
		if (spawnResult?.error) {
			msgLines.push("", `⚠️ Auto-spawn failed: ${spawnResult.error}`);
		}
	}

	ctx.notify(msgLines.join("\n"), "info");
	return false;
}

/** Focus mode — filtered board view */
async function handleFocus(ctx: CommandContext): Promise<boolean> {
	if (!ctx.hasUI) {
		ctx.notify(t("command.requires_interactive", ERR_REQUIRES_INTERACTIVE), "error");
		return false;
	}

	const parts = ctx.input.split(" ");
	if (parts.length < 2) {
		ctx.notify(renderClankerBoard(120), "info");
		return false;
	}

	const filter = parts[1];
	const filteredTasks = selectFilteredTasks(getState(), filter);

	try {
		const board = renderClankerBoard(process.stdout.columns || 120, [...filteredTasks]);
		ctx.notify(board, "info");
	} catch {
		// Fallback to unfiltered board
		ctx.notify(renderClankerBoard(120), "info");
	}
	return false;
}

/** Natural language interception — treat as new work item */
async function handleIntercept(ctx: CommandContext): Promise<boolean> {
	const result = applyTaskMutation(getState(), "create", { subject: ctx.input });
	commitState(result.state);
	ctx.notify(`✅ Added: ${ctx.input}`, "info");
	return true; // Re-render board
}

// ---------------------------------------------------------------------------
// Main route
// ---------------------------------------------------------------------------

/**
 * Route a /clanker command to its handler.
 */
export async function routeCommand(
	input: string,
	notify: (msg: string, level: string) => void,
	hasUI: boolean,
): Promise<void> {
	const subcommand = input.split(" ")[0].toLowerCase();
	const ctx: CommandContext = { input, subcommand, notify, hasUI };

	// Empty command — show board
	if (!input) {
		await handleEmpty(ctx);
		return;
	}

	// Known subcommand
	const handler = handlers[subcommand];
	if (handler) {
		await handler(ctx);
		return;
	}

	// Natural language interception — treat as work item
	await handleIntercept(ctx);

	// Re-render board after interception if possible
	if (hasUI) {
		try {
			const board = renderClankerBoard(process.stdout.columns || 120);
			notify(board, "info");
		} catch {
			// No fallback needed
		}
	}
}