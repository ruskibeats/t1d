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
import { type TUI } from "@earendil-works/pi-tui";
import { renderClankerBoard } from "./view/board.js";
import { getState } from "./state/store.js";

const WIDGET_KEY = "clanker-ops-todos";
const LEGACY_WIDGET_KEY = "rpiv-todos";

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
		const tasks = getState().tasks;
		return renderClankerBoard(tasks, { width }).split("\n");
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