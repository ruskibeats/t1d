/**
 * Master-Detail Board Component — Full-screen workspace for Clanker Ops.
 *
 * Uses alternate screen buffer for clean takeover of terminal area.
 * Layout: [Navigation Rail] [Task List] [Inspector/Reader]
 */

import type { Component, TUI } from "@mariozechner/pi-tui";
import { existsSync, readFileSync } from "node:fs";
import { getState } from "../state/store.js";
import type { Task } from "../tool/types.js";

// ---------------------------------------------------------------------------
// ANSI helpers - restrained color palette
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

// ---------------------------------------------------------------------------
// Tab definition
// ---------------------------------------------------------------------------

type Tab = "overview" | "plan" | "edit";

// ---------------------------------------------------------------------------
// Master-Detail Board Component
// ---------------------------------------------------------------------------

export interface MasterDetailBoardOptions {
	leftRailWidth?: number;  // Width for navigation rail (default 20)
	listWidth?: number;      // Width for task list (percentage, default 35)
}

export class MasterDetailBoard implements Component {
	private scrollOffset = 0;
	private selectedIndex = 0;
	private activeTab: Tab = "overview";
	private planScrollOffset = 0;
	private leftRailWidth: number;
	private listWidth: number;
	private tui: TUI | undefined;
	private done: (() => void) | undefined;

	constructor(options: MasterDetailBoardOptions = {}) {
		this.leftRailWidth = options.leftRailWidth ?? 20;
		this.listWidth = options.listWidth ?? 35;
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

		// Tab keys - overview/plan/edit only
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
			this.selectedIndex = Math.max(0, this.selectedIndex - 1);
			this.ensureSelectedVisible();
			this.activeTab = "overview";
			this.tui?.requestRender();
		} else if (data === "\x1b[B") {
			// Down arrow - move selection
			this.selectedIndex = Math.min(Math.max(0, tasks.length - 1), this.selectedIndex + 1);
			this.ensureSelectedVisible();
			this.activeTab = "overview";
			this.tui?.requestRender();
		} else if (data === "j" || data === "J") {
			if (this.activeTab === "plan") {
				this.planScrollOffset += 1;
			} else {
				this.selectedIndex = Math.min(Math.max(0, tasks.length - 1), this.selectedIndex + 1);
			}
			this.ensureSelectedVisible();
			this.tui?.requestRender();
		} else if (data === "k" || data === "K") {
			if (this.activeTab === "plan") {
				this.planScrollOffset = Math.max(0, this.planScrollOffset - 1);
			} else {
				this.selectedIndex = Math.max(0, this.selectedIndex - 1);
			}
			this.ensureSelectedVisible();
			this.tui?.requestRender();
		} else if (data === " ") {
			if (this.activeTab === "plan") this.planScrollOffset += 5;
			this.tui?.requestRender();
		} else if (data === "b" || data === "B") {
			if (this.activeTab === "plan") this.planScrollOffset = Math.max(0, this.planScrollOffset - 5);
			this.tui?.requestRender();
		} else if (data === "q" || data === "\x1b") {
			// Exit workspace
			this.tui?.hideOverlay();
			this.done?.();
		}
	}

	render(width: number): string[] {
		const tasks = this.getVisibleTasks();
		const selectedTask = tasks[this.selectedIndex];
		const termHeight = process.stdout.rows || 24;

		// Calculate pane widths
		const leftRailW = this.leftRailWidth;
		const listW = Math.floor((width - leftRailW - 1) * this.listWidth / 100);
		const inspectorW = width - leftRailW - 1 - listW - 1;

		const result: string[] = [];

		// Build header (full width)
		result.push(this.renderHeader(width));

		// Build content rows
		for (let row = 1; row < termHeight - 3; row++) {
			const leftRail = this.renderLeftRail(row);
			const taskList = this.renderTaskList(tasks, row, listW);
			const inspector = this.renderInspector(selectedTask, row, inspectorW);
			result.push(`${leftRail}│${taskList}│${inspector}`);
		}

		// Footer
		result.push(this.renderFooter(width));

		return result;
	}

	private renderHeader(width: number): string {
		const title = S.bold("Clanker Ops");
		const counts = this.getTaskCounts();
		const subtitle = S.gray(`${counts.total} tasks · ${counts.todo} todo · ${counts.done} done`);
		const padding = width - title.length - 2 - subtitle.length;
		return ` ${title} ${" ".repeat(Math.max(0, padding))}${subtitle}`;
	}

	private renderLeftRail(row: number): string {
		const items = ["Boards", "Views", "Tags", "Owners"];
		if (row >= 1 && row <= items.length + 1) {
			const idx = row - 1;
			const label = idx < items.length ? items[idx] : "";
			return S.gray(label.padEnd(this.leftRailWidth - 1));
		}
		return " ".repeat(this.leftRailWidth);
	}

	private renderTaskList(tasks: readonly Task[], row: number, width: number): string {
		const visibleCount = process.stdout.rows - 5; // Account for header/footer
		const taskRow = row - 1;

		if (taskRow < 0 || taskRow >= visibleCount) return "".padEnd(width);
		if (tasks.length === 0) return S.gray("No tasks".padEnd(width));

		const taskIndex = this.scrollOffset + taskRow;
		if (taskIndex >= tasks.length) return "".padEnd(width);

		const task = tasks[taskIndex];
		const isSelected = taskIndex === this.selectedIndex;
		const statusMark = this.getStatusMark(task.status);

		let line = isSelected ? S.reverse(" ") : " ";
		line += isSelected ? S.bold(statusMark) : statusMark;
		line += " ";
		line += isSelected ? S.bold(`#${task.id} ${task.item || ""}`.slice(0, width - 6)) : `#${task.id} ${task.item || ""}`.slice(0, width - 6);

		return line.padEnd(width);
	}

	private renderInspector(task: Task | undefined, row: number, width: number): string {
		if (!task) {
			const placeholder = ["No task selected", "", "Select a task to view details", "", "", "↑↓ to navigate", "P for plan", "E for edit"];
			return placeholder[row - 1] ? S.gray(placeholder[row - 1].padEnd(width)) : "".padEnd(width);
		}

		if (this.activeTab === "overview") {
			const lines = [
				`#${task.id} ${S.bold(task.item)}`,
				"",
				`Status: ${this.formatStatus(task.status)}`,
				task.assigned ? `Owner: ${task.assigned}` : "",
				task.tags && task.tags.length > 0 ? `Tags: ${task.tags.map(t => "#" + t).join(" ")}` : "",
				"",
				task.description || "",
				task.planFile ? `${S.cyan("📄")} ${task.planFile}` : "",
			];
			return lines[row - 1] ? lines[row - 1].slice(0, width).padEnd(width) : "".padEnd(width);
		}

		if (this.activeTab === "plan") {
			return this.renderPlanContent(task, row, width);
		}

		if (this.activeTab === "edit") {
			const lines = [
				`#${task.id} Edit Mode`,
				"",
				`Owner: ${task.assigned || ""}`,
				task.tags && task.tags.length > 0 ? `Tags: ${task.tags.map(t => "#" + t).join(" ")}` : "",
				"",
				S.gray("Save: Enter · Cancel: Esc"),
			];
			return lines[row - 1] ? lines[row - 1].slice(0, width).padEnd(width) : "".padEnd(width);
		}

		return "".padEnd(width);
	}

	private renderPlanContent(task: Task, row: number, width: number): string {
		if (!task.planFile) {
			return S.gray("No plan file. Press P to view plan if available.".padEnd(width));
		}

		const planPath = `.pi/todo-plans/${task.planFile}`;
		if (!existsSync(planPath)) {
			return S.gray(`Plan not found: ${task.planFile}`.padEnd(width));
		}

		try {
			const content = readFileSync(planPath, "utf-8");
			const lines = content.split("\n");
			const planRow = row - 1;
			const visibleLine = this.planScrollOffset + planRow;

			if (visibleLine < lines.length) {
				return lines[visibleLine].slice(0, width).padEnd(width);
			}
			return "".padEnd(width);
		} catch {
			return S.gray("Failed to read plan".padEnd(width));
		}
	}

	private renderFooter(width: number): string {
		const tabs = [
			this.activeTab === "overview" ? S.bold("[Overview]") : S.gray("[Overview]"),
			this.activeTab === "plan" ? S.bold("[Plan]") : S.gray("[Plan]"),
			this.activeTab === "edit" ? S.bold("[Edit]") : S.gray("[Edit]"),
		];
		const help = `${S.gray("↑↓ navigate · P plan · E edit · q quit")}`;
		const padding = width - tabs.join(" ").length - help.length - 2;
		return ` ${tabs.join(" ")} ${" ".repeat(Math.max(0, padding))}${help}`;
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
		const visibleCount = (process.stdout.rows || 24) - 5;
		if (this.selectedIndex < this.scrollOffset) {
			this.scrollOffset = this.selectedIndex;
		} else if (this.selectedIndex >= this.scrollOffset + visibleCount) {
			this.scrollOffset = this.selectedIndex - visibleCount + 1;
		}
	}

	private getVisibleTasks(): readonly Task[] {
		return getState().tasks.filter(t => t.status !== "deleted");
	}
}