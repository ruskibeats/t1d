/**
 * Master-Detail Board Component — Full-screen terminal workspace for Clanker Ops.
 *
 * Uses alternate screen buffer for clean takeover of terminal area.
 * Layout: [Navigation Rail] [Task List] [Inspector/Reader]
 *
 * Visual structure:
 * ┌────────────────────────────────────────────────────────┐
 * │ Header (title + counts)                                │
 * ├──────────────┬────────────────────────┬────────────────┤
 * │ Left rail    │ Task list            │ Inspector      │
 * │              │                        │                │
 * ├──────────────┴────────────────────────┴────────────────┤
 * │ Footer (tabs + shortcuts)                              │
 * └────────────────────────────────────────────────────────┘
 */

import type { Component, TUI } from "@mariozechner/pi-tui";
import { existsSync, readFileSync } from "node:fs";
import { getState, getNextId } from "../state/store.js";
import type { Task } from "../tool/types.js";

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
	reverse: (v: string) => `\x1b[7m${v}\x1b[0m`,
};

// Box drawing
const BOX = {
	h: "─", v: "│", tl: "┌", tr: "┐", bl: "└", br: "┘",
	tt: "┬", bb: "┴", lt: "├", rt: "┤", cross: "┼",
	hh: "─", vv: "│",
};

// ---------------------------------------------------------------------------
// Tab definition
// ---------------------------------------------------------------------------

type Tab = "overview" | "plan" | "edit";

// ---------------------------------------------------------------------------
// Layout constants
// ---------------------------------------------------------------------------

const LAYOUT = {
	headerHeight: 1,
	footerHeight: 1,
	minWidth: 80,
	leftRailWidth: 18,  // Boards, Views, Tags, Owners sections
	listMinWidth: 30,
	separator: " │ ",
};

// Fixed column boundaries for the three panes
function getColumnBoundaries(width: number) {
	const leftW = LAYOUT.leftRailWidth;
	const listW = Math.max(LAYOUT.listMinWidth, Math.floor((width - leftW - 3) * 0.35));
	const inspectorW = width - leftW - listW - 3;
	return { leftW, listW, inspectorW, separators: [leftW, leftW + listW + 1] };
}

// ---------------------------------------------------------------------------
// Master-Detail Board Component
// ---------------------------------------------------------------------------

export interface MasterDetailBoardOptions {
	leftRailWidth?: number;
}

export class MasterDetailBoard implements Component {
	private scrollOffset = 0;
	private selectedIndex = 0;
	private activeTab: Tab = "overview";
	private planScrollOffset = 0;
	private leftRailWidth: number;
	private tui: TUI | undefined;
	private done: (() => void) | undefined;
	private termWidth = 0;
	private termHeight = 0;

	constructor(options: MasterDetailBoardOptions = {}) {
		this.leftRailWidth = options.leftRailWidth ?? LAYOUT.leftRailWidth;
	}

	setTUI(tui: TUI): void {
		this.tui = tui;
	}

	setDone(done: () => void): void {
		this.done = done;
	}

	invalidate(): void {
		this.scrollOffset = 0;
		this.planScrollOffset = 0;
	}

	handleInput(data: string): void {
		const tasks = this.getVisibleTasks();

		// Tab switches
		if (data === "O" || data === "o") {
			this.activeTab = "overview";
			this.tui?.requestRender();
		} else if (data === "P" || data === "p") {
			const selectedTask = tasks[this.selectedIndex];
			if (selectedTask?.planFile) this.activeTab = "plan";
			this.tui?.requestRender();
		} else if (data === "E" || data === "e") {
			this.activeTab = "edit";
			this.tui?.requestRender();
		} else if (data === "\x1b[A") {
			// Up arrow - move selection
			if (this.activeTab === "plan") {
				this.planScrollOffset = Math.max(0, this.planScrollOffset - 1);
			} else {
				this.selectedIndex = Math.max(0, this.selectedIndex - 1);
			}
			this.ensureSelectedVisible();
			this.tui?.requestRender();
		} else if (data === "\x1b[B") {
			// Down arrow - move selection
			if (this.activeTab === "plan") {
				this.planScrollOffset += 1;
			} else {
				this.selectedIndex = Math.min(Math.max(0, tasks.length - 1), this.selectedIndex + 1);
			}
			this.ensureSelectedVisible();
			this.tui?.requestRender();
		} else if (data === " " || data === "b" || data === "B") {
			if (data === " " && this.activeTab === "plan") this.planScrollOffset += 5;
			if (data === "B" && this.activeTab === "plan") this.planScrollOffset = Math.max(0, this.planScrollOffset - 5);
			this.tui?.requestRender();
		} else if (data === "q" || data === "\x1b") {
			// Exit workspace - both hide overlay AND resolve promise
			this.tui?.hideOverlay();
			this.done?.();
		}
	}

	render(width: number): string[] {
		this.termWidth = width;
		this.termHeight = process.stdout.rows || 24;

		const { leftW, listW, inspectorW } = getColumnBoundaries(width);

		// Calculate visible task count (body rows minus header/footer)
		const bodyRows = this.termHeight - 3; // header + footer + top border

		const result: string[] = [];

		// Top border
		result.push(this.renderTopBorder(width));

		// Header
		result.push(this.renderHeader(width));

		// Separator after header
		result.push(this.renderHeaderSeparator(width, leftW, listW));

		// Body rows - three panes
		const tasks = this.getVisibleTasks();
		const selectedTask = tasks[this.selectedIndex];

		for (let row = 0; row < bodyRows; row++) {
			const leftRail = this.renderLeftRail(row, leftW);
			const taskList = this.renderTaskList(tasks, row, listW);
			const inspector = this.renderInspector(selectedTask, row, inspectorW);

			// Build the row with exact column boundaries
			const sep1 = BOX.v;
			const sep2 = BOX.v;
			result.push(`${leftRail}${sep1}${taskList}${sep2}${inspector}`);
		}

		// Separator before footer
		result.push(this.renderFooterSeparator(width, leftW, listW));

		// Footer
		result.push(this.renderFooter(width));

		// Bottom border
		result.push(this.renderBottomBorder(width));

		return result;
	}

	private renderTopBorder(width: number): string {
		return BOX.tl + BOX.h.repeat(width - 2) + BOX.tr;
	}

	private renderBottomBorder(width: number): string {
		return BOX.bl + BOX.h.repeat(width - 2) + BOX.br;
	}

	private renderHeader(width: number): string {
		const counts = this.getTaskCounts();
		const title = S.bold("Clanker Ops");
		const subtitle = `${counts.total} tasks │ ${counts.todo} todo │ ${counts.done} done`;
		const padding = width - title.length - subtitle.length - 2;
		return `${BOX.v} ${title} ${subtitle.padStart(Math.max(0, padding))} ${BOX.v}`;
	}

	private renderHeaderSeparator(width: number, leftW: number, listW: number): string {
		const { separators } = getColumnBoundaries(width);
		let row = BOX.lt;
		row += BOX.h.repeat(leftW + 1);
		row += BOX.cross;
		row += BOX.h.repeat(listW + 1);
		row += BOX.cross;
		row += BOX.h.repeat(width - leftW - listW - 4);
		row += BOX.rt;
		return row;
	}

	private renderFooterSeparator(width: number, leftW: number, listW: number): string {
		const { separators } = getColumnBoundaries(width);
		let row = BOX.lt;
		row += BOX.h.repeat(leftW + 1);
		row += BOX.cross;
		row += BOX.h.repeat(listW + 1);
		row += BOX.cross;
		row += BOX.h.repeat(width - leftW - listW - 4);
		row += BOX.rt;
		return row;
	}

	private renderFooter(width: number): string {
		const tabs = [
			this.activeTab === "overview" ? S.bold("[Overview]") : S.gray("[Overview]"),
			this.activeTab === "plan" ? S.bold("[Plan]") : S.gray("[Plan]"),
			this.activeTab === "edit" ? S.bold("[Edit]") : S.gray("[Edit]"),
		];
		const help = `${S.gray("↑↓ move │ P plan │ O overview │ E edit │ q quit")}`;
		const inner = ` ${tabs.join(" ")} │ ${help} `;
		const padding = width - inner.length - 2;
		return `${BOX.v}${inner.padEnd(width - 2)}${BOX.v}`;
	}

	private renderLeftRail(row: number, width: number): string {
		const sections = [
			{ name: "Boards", items: ["default", "ios", "backend"] },
			{ name: "Views", items: ["all", "todo", "done"] },
			{ name: "Tags", items: ["#graph", "#ios", "#backend"] },
			{ name: "Owners", items: ["@worker", "@builder"] },
		];

		let content = "";
		let cursor = 0;

		for (const section of sections) {
			// Section header
			content += S.bold(section.name);
			cursor++;
			if (cursor > row) break;

			// Items under section
			for (const item of section.items) {
				const isFirst = section.name === "Boards" && item === "default";
				const marker = isFirst ? S.accent("▶ ") : "  ";
				content += `${marker}${item}`;
				cursor++;
				if (cursor > row) break;
			}
			if (cursor > row) break;
		}

		return content.padEnd(width);
	}

	private renderTaskList(tasks: readonly Task[], row: number, width: number): string {
		if (tasks.length === 0) return S.gray("No tasks".padEnd(width));

		const taskIndex = this.scrollOffset + row;
		if (taskIndex >= tasks.length) return "".padEnd(width);

		const task = tasks[taskIndex];
		const isSelected = taskIndex === this.selectedIndex;
		const statusMark = this.getStatusMark(task.status);

		let line = isSelected ? S.reverse(" ") : " ";
		line += isSelected ? S.bold(statusMark) : statusMark;
		line += isSelected ? S.bold(` #${task.id} ${task.item || ""}`.slice(0, width - 6)) : ` #${task.id} ${task.item || ""}`.slice(0, width - 6);

		return line.padEnd(width);
	}

	private renderInspector(task: Task | undefined, row: number, width: number): string {
		if (!task) {
			const lines = ["No task selected", "", "↑↓ to navigate", "", "P for plan", "E for edit"];
			return (lines[row] ? S.gray(lines[row]) : "").padEnd(width);
		}

		if (this.activeTab === "overview") {
			const lines = [
				`#${task.id} ${S.bold(task.item)}`,
				"",
				`Status: ${this.formatStatus(task.status)}`,
				task.assigned ? `Owner: ${task.assigned}` : "",
				task.tags?.length ? `Tags: ${task.tags.map(t => `#${t}`).join(" ")}` : "",
				"",
				task.description || "",
				task.planFile ? `${S.cyan("📄")} ${task.planFile}` : "",
			];
			return (lines[row] || "").padEnd(width);
		}

		if (this.activeTab === "plan") {
			return this.renderPlanContent(task, row, width);
		}

		// Edit tab
		const lines = [
			`#${task.id} Edit Mode`,
			"",
			`Owner: ${task.assigned || ""}`,
			task.tags?.length ? `Tags: ${task.tags.map(t => `#${t}`).join(" ")}` : "",
			"",
			S.gray("Save: Enter │ Cancel: Esc"),
		];
		return (lines[row] || "").padEnd(width);
	}

	private renderPlanContent(task: Task, row: number, width: number): string {
		if (!task.planFile) {
			return S.gray("No plan file. Press P to view plan if available.").padEnd(width);
		}

		const planPath = `.pi/todo-plans/${task.planFile}`;
		if (!existsSync(planPath)) {
			return S.gray(`Plan not found: ${task.planFile}`).padEnd(width);
		}

		try {
			const content = readFileSync(planPath, "utf-8");
			const lines = content.split("\n");
			if (this.planScrollOffset + row < lines.length) {
				return lines[this.planScrollOffset + row].slice(0, width).padEnd(width);
			}
			return "".padEnd(width);
		} catch {
			return S.gray("Failed to read plan").padEnd(width);
		}
	}

	private formatStatus(status: string): string {
		const map: Record<string, string> = {
			in_progress: S.yellow("in_progress"),
			completed: S.green("completed"),
			failed: S.accent("failed"),
			pending: S.gray("pending"),
			deferred: S.gray("deferred"),
		};
		return map[status] || status;
	}

	private getStatusMark(status: string): string {
		const marks: Record<string, string> = {
			in_progress: "▶",
			completed: "✓",
			failed: "✗",
			pending: "○",
			deferred: "◌",
		};
		return marks[status] || "•";
	}

	private getTaskCounts(): { total: number; todo: number; done: number } {
		const tasks = this.getVisibleTasks();
		return {
			total: tasks.length,
			todo: tasks.filter(t => t.status !== "completed").length,
			done: tasks.filter(t => t.status === "completed").length,
		};
	}

	private ensureSelectedVisible(): void {
		const bodyRows = (process.stdout.rows || 24) - 3;
		if (this.selectedIndex < this.scrollOffset) {
			this.scrollOffset = this.selectedIndex;
		} else if (this.selectedIndex >= this.scrollOffset + bodyRows) {
			this.scrollOffset = this.selectedIndex - bodyRows + 1;
		}
	}

	private getVisibleTasks(): readonly Task[] {
		return getState().tasks.filter(t => t.status !== "deleted");
	}
}