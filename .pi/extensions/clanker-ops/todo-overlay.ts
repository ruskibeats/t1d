/**
 * todo-overlay.ts — Persistent widget showing Clanker Ops work items above the editor.
 *
 * Lifecycle controller for Pi's `setWidget` contract: factory-form
 * registration in widgetContainerAbove, register-once + requestRender()
 * refresh, 12-line collapse-not-scroll, auto-hide when empty.
 *
 * Reads live state via `getState()` at render time — NEVER `replayFromBranch`
 * from `tool_execution_end` (branch is stale; `message_end` runs after).
 */

import type { ExtensionUIContext, Theme } from "@earendil-works/pi-coding-agent";
import { type TUI } from "@mariozechner/pi-tui";
import { renderClankerBoardCompact } from "./view/board.js";
import { getState } from "./state/store.js";
import { selectOverlayLayout } from "./state/selectors.js";
import { MasterDetailBoard } from "./view/master-detail-board.js";

const WIDGET_KEY = "clanker-ops-todos";
const LEGACY_WIDGET_KEY = "rpiv-todos";
const MAX_WIDGET_LINES = 12;

export class TodoOverlay {
	private uiCtx: ExtensionUIContext | undefined;
	private widgetRegistered = false;
	private tui: TUI | undefined;

	setUICtx(ctx: ExtensionUIContext): void {
		// Identity-compare so repeat session_start handlers are idempotent;
		// on identity change (/reload) invalidate so update() re-registers.
		if (ctx !== this.uiCtx) {
			this.uiCtx = ctx;
			this.widgetRegistered = false;
			this.tui = undefined;
		}
	}

	update(): void {
		if (!this.uiCtx) return;

		// Clean up legacy widget just in case
		this.uiCtx.setWidget(LEGACY_WIDGET_KEY, undefined);

		if (!this.widgetRegistered) {
			this.uiCtx.setWidget(
				WIDGET_KEY,
				(tui, theme) => {
					this.tui = tui;
					return {
						render: (width: number) => this.renderWidget(theme, width),
						invalidate: () => {
							this.widgetRegistered = false;
							this.tui = undefined;
						},
					};
				},
				{ placement: "aboveEditor" },
			);
			this.widgetRegistered = true;
		} else {
			this.tui?.requestRender();
		}
	}

	resetCompletedDisplayState(): void {
		// No-op: state is always fresh from getState()
	}

	hideCompletedTasksFromPreviousTurn(): void {
		this.tui?.requestRender();
	}

	private renderWidget(theme: Theme, width: number): string[] {
		this.uiCtx?.setStatus(WIDGET_KEY, theme.fg("accent", "Clanker Ops"));
		const state = getState();

		// Apply overlay layout to respect height budget
		const taskBudget = Math.max(1, MAX_WIDGET_LINES - 8 - 1);
		const { visible, hiddenCompleted, truncatedTail } = selectOverlayLayout(
			state,
			taskBudget,
		);

		// Use compact renderer for widget - cleaner for limited space
		const boardOutput = renderClankerBoardCompact(visible, { width });
		const lines = boardOutput.split("\n");

		// Show overflow info
		if (hiddenCompleted > 0 || truncatedTail > 0) {
			const parts: string[] = [];
			if (hiddenCompleted > 0) parts.push(`${hiddenCompleted} done`);
			if (truncatedTail > 0) parts.push(`${truncatedTail} more`);
			lines[0] = lines[0] + ` · ${parts.join(", ")}`;
		}

		return lines;
	}

	/**
	 * Show scrollable overlay for full board navigation.
	 * Call this from a command handler.
	 */
	showScrollableBoard(): void {
		if (!this.tui) return;

		const board = new MasterDetailBoard({ maxHeight: MAX_WIDGET_LINES, leftWidth: 45 });
		this.tui.showOverlay(board);
	}

	/**
	 * Show scrollable overlay from a command (passes tui directly).
	 */
	static showFromCommand(tui: TUI): void {
		const board = new MasterDetailBoard({ maxHeight: 30, leftWidth: 45 });
		tui.showOverlay(board);
	}

	dispose(): void {
		if (this.uiCtx) {
			this.uiCtx.setWidget(WIDGET_KEY, undefined);
			this.uiCtx.setStatus(WIDGET_KEY, undefined);
		}
		this.widgetRegistered = false;
		this.tui = undefined;
		this.uiCtx = undefined;
	}
}