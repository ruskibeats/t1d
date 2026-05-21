/**
 * clanker-ops — Pi extension. Registers the `todo` tool (LLM task management),
 * `/clanker` command (interactive board), and the persistent Clanker Ops
 * overlay widget above the editor.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { I18N_NAMESPACE } from "./state/i18n-bridge.js";
import { replayFromBranch } from "./state/replay.js";
import { replaceState } from "./state/store.js";
import { registerClankerCommand, registerTodoTool, TOOL_NAME } from "./todo.js";
import { TodoOverlay } from "./todo-overlay.js";
import { handleIntercomEvent, pollDispatchArtifacts } from "./intercom-handler.js";
import { formatCompactContext, formatDetailContext } from "./injector/context-injector.js";

type TranslationMap = Readonly<Record<string, string>>;

function loadLocale(code: string): TranslationMap {
	try {
		return JSON.parse(
			readFileSync(fileURLToPath(new URL(`./locales/${code}.json`, import.meta.url)), "utf-8"),
		) as TranslationMap;
	} catch {
		return {};
	}
}

export default function (pi: ExtensionAPI) {
	let todoOverlay: TodoOverlay | undefined;

	registerTodoTool(pi);
	registerClankerCommand(pi);

	pi.on("session_start", async (_event, ctx) => {
		replaceState(replayFromBranch(ctx));
		// Catch up on background dispatch status after session restart
		pollDispatchArtifacts();
		if (ctx.hasUI) {
			todoOverlay ??= new TodoOverlay();
			todoOverlay.setUICtx(ctx.ui);
			todoOverlay.resetCompletedDisplayState();
			todoOverlay.update();
		}
	});

	pi.on("session_compact", async (_event, ctx) => {
		replaceState(replayFromBranch(ctx));
		todoOverlay?.resetCompletedDisplayState();
		todoOverlay?.update();
	});

	pi.on("session_tree", async (_event, ctx) => {
		replaceState(replayFromBranch(ctx));
		todoOverlay?.resetCompletedDisplayState();
		todoOverlay?.update();
	});

	pi.on("session_shutdown", async () => {
		todoOverlay?.dispose();
		todoOverlay = undefined;
	});

	pi.on("tool_execution_end", async (event) => {
		if (event.toolName !== TOOL_NAME || event.isError) return;
		todoOverlay?.update();
	});

	// Listen for subagent control events (needs_attention, active_long_running, completion_guard)
	pi.on("subagent_control_event", async (event) => {
		handleIntercomEvent(event as never);
		todoOverlay?.update();
	});

	pi.on("subagent_control_intercom_event", async (event) => {
		if (event && typeof event === "object" && "event" in event) {
			handleIntercomEvent((event as { event: unknown }).event as never);
			todoOverlay?.update();
		}
	});

	pi.on("agent_start", async () => {
		todoOverlay?.hideCompletedTasksFromPreviousTurn();
	});
}