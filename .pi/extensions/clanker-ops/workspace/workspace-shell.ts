/**
 * Clanker Workspace Shell - Full-screen terminal workspace
 *
 * Orchestrates three-pane layout and manages board/task state.
 */

import type { Component, TUI } from "@mariozechner/pi-tui";
import type { Task } from "../tool/types.js";
import type { Tab } from "../ui/types.js";

// ---------------------------------------------------------------------------
// ANSI helpers - restrained palette
// ---------------------------------------------------------------------------

const S = {
	bold: (v: string) => `\x1b[1m${v}\x1b[0m`,
	gray: (v: string) => `\x1b[90m${v}\x1b[0m`,
	accent: (v: string) => `\x1b[38;5;33m${v}\x1b[0m`,
	green: (v: string) => `\x1b[32m${v}\x1b[0m`,
	cyan: (v: string) => `\x1b[36m${v}\x1b[0m`,
	yellow: (v: string) => `\x1b[33m${v}\x1b[0m`,
};

// ---------------------------------------------------------------------------
// Workspace State
// ---------------------------------------------------------------------------

export interface WorkspaceState {
	activeTaskId: string | null;
	activeTab: Tab;
	planScrollOffset: number;
	query: string;
}

// ---------------------------------------------------------------------------
// Workspace Shell Component
// ---------------------------------------------------------------------------

export interface WorkspaceOptions {
	leftRailWidth?: number;
	listWidthPercent?: number;
}

export class WorkspaceShell implements Component {
	private state: WorkspaceState = {
		activeTaskId: null,
		activeTab: "overview",
		planScrollOffset: 0,
		query: "",
	};
	private scrollOffset = 0;
	private tui: TUI | undefined;
	private done: (() => void) | undefined;
	private leftRailWidth: number;
	private listWidthPercent: number;

	constructor(options: WorkspaceOptions = {}) {
		this.leftRailWidth = options.leftRailWidth ?? 20;
		this.listWidthPercent = options.listWidthPercent ?? 35;
	}

	setTUI(tui: TUI): void {
		this.tui = tui;
	}

	setDone(done: () => void): void {
		this.done = done;
	}

	setActiveTask(taskId: string | null): void {
		this.state.activeTaskId = taskId;
		this.scrollIntoView();
	}

	setTab(tab: Tab): void {
		this.state.activeTab = tab;
		this.state.planScrollOffset = 0;
	}

	invalidate(): void {
		this.scrollOffset = 0;
		this.state.planScrollOffset = 0;
	}

	handleInput(data: string): void {
		// Navigation keys are handled by sub-components
		// ESC should exit the workspace
		if (data === "q" || data === "\x1b") {
			this.tui?.hideOverlay();
			this.done?.();
		}
	}

	render(width: number): string[] {
		const termHeight = process.stdout.rows || 24;
		const result: string[] = [];

		// Header
		result.push(this.renderHeader(width));

		// Content rows
		for (let row = 1; row < termHeight - 2; row++) {
			result.push(this.renderContentRow(row, width));
		}

		// Footer
		result.push(this.renderFooter(width));

		return result;
	}

	private renderHeader(width: number): string {
		const title = S.bold("Clanker Ops Workspace");
		const padding = width - title.length - 2;
		return ` ${title}${" ".repeat(Math.max(0, padding))}`;
	}

	private renderContentRow(row: number, width: number): string {
		const leftRail = " ".repeat(this.leftRailWidth);
		const listWidth = Math.floor((width - this.leftRailWidth - 1) * this.listWidthPercent / 100);
		const inspectorWidth = width - this.leftRailWidth - 1 - listWidth - 1;

		return `${leftRail}│${" ".repeat(listWidth)}│${" ".repeat(inspectorWidth)}`;
	}

	private renderFooter(width: number): string {
		const help = S.gray("↑↓ navigate · Tab focus · P plan · O overview · E edit · Q quit");
		return ` ${help}${" ".repeat(Math.max(0, width - help.length - 1))}`;
	}

	private scrollIntoView(): void {
		// Implementation depends on task list component
	}
}