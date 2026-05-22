/**
 * Master-Detail Board Component — Two-pane task browser with plan preview.
 *
 * Left pane: task list from .pi/todo-state.json
 * Right pane: inspector with tabs for Overview/Checklist/Notes/Plan
 */

import type { Component, TUI } from "@mariozechner/pi-tui";
import { existsSync, readFileSync } from "node:fs";
import { getState } from "../state/store.js";
import type { Task } from "../tool/types.js";

// ---------------------------------------------------------------------------
// ANSI helpers
// ---------------------------------------------------------------------------

const ansi = {
	bold: (v: string) => `\x1b[1m${v}\x1b[0m`,
	gray: (v: string) => `\x1b[90m${v}\x1b[0m`,
	border: (v: string) => `\x1b[38;5;33m${v}\x1b[0m`,
	green: (v: string) => `\x1b[32m${v}\x1b[0m`,
	cyan: (v: string) => `\x1b[36m${v}\x1b[0m`,
	yellow: (v: string) => `\x1b[33m${v}\x1b[0m`,
};

// ---------------------------------------------------------------------------
// Tab definition
// ---------------------------------------------------------------------------

type Tab = "overview" | "checklist" | "notes" | "plan";

// ---------------------------------------------------------------------------
// Master-Detail Board Component
// ---------------------------------------------------------------------------

export interface MasterDetailBoardOptions {
	leftWidth?: number;  // Percentage of width for left pane (default 40)
	maxHeight?: number;  // Maximum height in lines
}

export class MasterDetailBoard implements Component {
	private scrollOffset = 0;
	private selectedIndex = 0;
	private activeTab: Tab = "overview";
	private planScrollOffset = 0;
	private maxViewLines: number;
	private leftWidth: number;
	private tui: TUI | undefined;
	private done: (() => void) | undefined;

	constructor(options: MasterDetailBoardOptions = {}) {
		this.maxViewLines = options.maxHeight ?? 20;
		this.leftWidth = options.leftWidth ?? 40;
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

		// Handle tab navigation when Plan tab is active and showing content
		if (data === "\t" || data === "h") {
			// Cycle tabs: overview -> checklist -> notes -> plan -> overview
			const tabs: Tab[] = ["overview", "checklist", "notes", "plan"];
			const currentIndex = tabs.indexOf(this.activeTab);
			this.activeTab = tabs[(currentIndex + 1) % tabs.length];
			this.planScrollOffset = 0; // Reset plan scroll on tab change
			this.tui?.requestRender();
		} else if (data === "\x1b[Z") {
			// Shift+Tab - reverse cycle
			const tabs: Tab[] = ["overview", "checklist", "notes", "plan"];
			const currentIndex = tabs.indexOf(this.activeTab);
			this.activeTab = tabs[(currentIndex - 1 + tabs.length) % tabs.length];
			this.planScrollOffset = 0;
			this.tui?.requestRender();
		} else if (data === "O" || data === "o") {
			// Return to overview tab
			this.activeTab = "overview";
			this.tui?.requestRender();
		} else if (data === "P" || data === "p") {
			// Open plan tab for selected task
			const selectedTask = tasks[this.selectedIndex];
			if (selectedTask?.planFile) {
				this.activeTab = "plan";
				this.planScrollOffset = 0;
			}
			this.tui?.requestRender();
		} else if (data === "\x1b[A") {
			// Up arrow - move selection
			this.selectedIndex = Math.max(0, this.selectedIndex - 1);
			this.ensureSelectedVisible();
			this.activeTab = "overview"; // Return to overview on navigation
			this.tui?.requestRender();
		} else if (data === "\x1b[B") {
			// Down arrow - move selection
			this.selectedIndex = Math.min(Math.max(0, tasks.length - 1), this.selectedIndex + 1);
			this.ensureSelectedVisible();
			this.activeTab = "overview"; // Return to overview on navigation
			this.tui?.requestRender();
		} else if (data === "j" || data === "J") {
			// Scroll down in plan view
			if (this.activeTab === "plan") {
				this.planScrollOffset += 1;
			} else {
				this.selectedIndex = Math.min(Math.max(0, tasks.length - 1), this.selectedIndex + 1);
				this.ensureSelectedVisible();
			}
			this.tui?.requestRender();
		} else if (data === "k" || data === "K") {
			// Scroll up in plan view
			if (this.activeTab === "plan") {
				this.planScrollOffset = Math.max(0, this.planScrollOffset - 1);
			} else {
				this.selectedIndex = Math.max(0, this.selectedIndex - 1);
				this.ensureSelectedVisible();
			}
			this.tui?.requestRender();
		} else if (data === " ") {
			// Page down in plan view
			if (this.activeTab === "plan") {
				this.planScrollOffset += Math.floor(this.maxViewLines / 2);
			}
			this.tui?.requestRender();
		} else if (data === "b") {
			// Page up in plan view
			if (this.activeTab === "plan") {
				this.planScrollOffset = Math.max(0, this.planScrollOffset - Math.floor(this.maxViewLines / 2));
			}
			this.tui?.requestRender();
		} else if (data === "q" || data === "\x1b") {
			// Close overlay on q or ESC
			this.tui?.hideOverlay();
			this.done?.();
		}
	}

	render(width: number): string[] {
		const tasks = this.getVisibleTasks();
		const selectedTask = tasks[this.selectedIndex];
		const widthNum = Math.max(40, width);
		const leftPaneWidth = Math.floor(widthNum * this.leftWidth / 100);
		const rightPaneWidth = widthNum - leftPaneWidth - 1; // Account for separator

		// Build left pane (task list)
		const leftLines = this.buildTaskList(tasks, leftPaneWidth);

		// Build right pane (inspector)
		const rightLines = this.buildInspector(selectedTask, rightPaneWidth);

		// Combine panes
		const result: string[] = [];
		const maxLines = Math.max(leftLines.length, rightLines.length);

		for (let i = 0; i < maxLines; i++) {
			const left = leftLines[i] || " ".repeat(leftPaneWidth);
			const right = rightLines[i] || "";
			result.push(`${left}│${right}`);
		}

		// Add help line if there's room
		if (leftLines.length + 1 <= this.maxViewLines) {
			const helpText = ansi.gray("↑↓ move · Tab switch · O overview · P plan · PgUp/PgDn scroll · Esc close");
			const padded = " ".repeat(leftPaneWidth) + "│" + helpText;
			result.push(padded);
		}

		return result.length > 0 ? result : ["No tasks"];
	}

	private buildTaskList(tasks: readonly Task[], width: number): string[] {
		const lines: string[] = [];
		const innerWidth = width - 2;

		// Header
		lines.push(ansi.border("┌" + "─".repeat(innerWidth) + "┐"));
		const headerText = ` Clanker Queue `.slice(0, innerWidth - 2);
		lines.push(ansi.border("│") + ansi.bold(headerText).padEnd(innerWidth + 1) + ansi.border("┆"));
		lines.push(ansi.border("├" + "─".repeat(innerWidth) + "┤"));

		// Task list with virtual scrolling
		const visibleCount = Math.max(0, this.maxViewLines - 4); // Account for header lines
		const maxScroll = Math.max(0, tasks.length - visibleCount);
		this.scrollOffset = Math.min(this.scrollOffset, maxScroll);

		for (let i = 0; i < visibleCount; i++) {
			const taskIndex = this.scrollOffset + i;
			if (taskIndex >= tasks.length) {
				lines.push(ansi.border("│") + "".padEnd(innerWidth + 1) + ansi.border("┆"));
				continue;
			}

			const task = tasks[taskIndex];
			const isSelected = taskIndex === this.selectedIndex;
			const statusMark = this.getStatusMark(task.status, isSelected);
			const taskText = `${isSelected ? ">" : " "} #${task.id} ${task.item}`.slice(0, innerWidth - 2);

			const line = isSelected
				? ansi.bold(statusMark + " " + taskText)
				: statusMark + " " + taskText;

			lines.push(ansi.border("│") + line.padEnd(innerWidth) + ansi.border("┆"));
		}

		// Scroll indicator
		if (tasks.length > visibleCount) {
			const totalPages = Math.ceil(tasks.length / visibleCount);
			const currentPage = Math.floor(this.scrollOffset / visibleCount) + 1;
			const indicator = `${ansi.gray("scroll: ")}${ansi.bold(`${currentPage}/${totalPages}`)}`;
			const lastLine = lines[lines.length - 1];
			if (lastLine) {
				lines[lines.length - 1] = lastLine.slice(0, -(indicator.length + 1)) + "  " + indicator + ansi.border("┆");
			}
		}

		// Footer
		lines.push(ansi.border("└" + "─".repeat(innerWidth) + "┘"));

		return lines;
	}

	private buildInspector(task: Task | undefined, width: number): string[] {
		const lines: string[] = [];
		const innerWidth = width - 2;

		// Header with tabs
		lines.push(ansi.border("┌" + "─".repeat(innerWidth) + "┐"));
		const tabNames: Tab[] = ["overview", "checklist", "notes", "plan"];
		const tabLabels = tabNames.map(t => {
			const base = t === "overview" ? "Details" : t.charAt(0).toUpperCase() + t.slice(1);
			const hasContent = t === "plan" ? !!task?.planFile : t !== "checklist" && t !== "notes";
			const isCurrent = this.activeTab === t;
			const indicator = isCurrent ? ansi.bold(base) : ansi.gray(base);
			return hasContent ? indicator : ansi.gray(`${base} (empty)`);
		}).join(" ");
		lines.push(ansi.border("│") + ` ${ansi.bold("Inspector")} ${tabLabels}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - ansi.gray(" ").length)) + ansi.border("┐"));
		lines.push(ansi.border("├" + "─".repeat(innerWidth) + "┤"));

		if (!task) {
			lines.push(ansi.border("│") + ansi.gray("No task selected").padEnd(innerWidth) + ansi.border("│"));
		} else {
			switch (this.activeTab) {
				case "overview":
					lines.push(...this.buildOverviewTab(task, innerWidth));
					break;
				case "plan":
					lines.push(...this.buildPlanTab(task, innerWidth));
					break;
				case "checklist":
					lines.push(...this.buildChecklistTab(task, innerWidth));
					break;
				case "notes":
					lines.push(...this.buildNotesTab(task, innerWidth));
					break;
			}
		}

		// Footer
		while (lines.length < this.maxViewLines - 2) {
			lines.push(ansi.border("│") + "".padEnd(innerWidth) + ansi.border("│"));
		}
		lines.push(ansi.border("└" + "─".repeat(innerWidth) + "┘"));

		return lines;
	}

	private buildOverviewTab(task: Task, width: number): string[] {
		const lines: string[] = [];
		const innerWidth = width - 2;

		// ID and status
		lines.push(ansi.border("│") + ` #${task.id} ${ansi.bold(task.item)}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - 10)) + ansi.border("│"));

		// Status and owner
		const statusColor = task.status === "in_progress" ? ansi.yellow(task.status) :
			task.status === "completed" ? ansi.green(task.status) :
			task.status === "failed" ? ansi.yellow(task.status) :
			ansi.gray(task.status);
		lines.push(ansi.border("│") + ` Status: ${statusColor}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - 20)) + ansi.border("│"));

		if (task.assigned) {
			lines.push(ansi.border("│") + ` Owner: ${task.assigned}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - 20)) + ansi.border("│"));
		}

		// Tags
		if (task.tags && task.tags.length > 0) {
			lines.push(ansi.border("│") + ` Tags: ${task.tags.map(t => `#${t}`).join(" ")}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - 20)) + ansi.border("│"));
		}

		// Description (truncated)
		if (task.description) {
			const desc = task.description.replace(/\n/g, " ").slice(0, innerWidth - 12);
			lines.push(ansi.border("│") + ` ${desc}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - desc.length)) + ansi.border("│"));
		}

		// Plan file reference
		if (task.planFile) {
			const planMarker = ansi.cyan("📄") + " " + task.planFile;
			lines.push(ansi.border("│") + ` ${planMarker}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - planMarker.length)) + ansi.border("│"));
		}

		return lines;
	}

	private buildPlanTab(task: Task, width: number): string[] {
		const lines: string[] = [];
		const innerWidth = width;

		if (!task.planFile) {
			const msg = ansi.gray("No plan file linked. Press 'P' to view plan if available.");
			lines.push(ansi.border("│") + ` ${msg}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - msg.length)) + ansi.border("│"));
			return lines;
		}

		const planPath = `.pi/todo-plans/${task.planFile}`;
		if (!existsSync(planPath)) {
			const msg = ansi.gray(`Plan file not found: ${task.planFile}`);
			lines.push(ansi.border("│") + ` ${msg}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - msg.length)) + ansi.border("│"));
			return lines;
		}

		try {
			const content = readFileSync(planPath, "utf-8");
			const planLines = content.split("\n");
			const visibleEnd = this.planScrollOffset + this.maxViewLines - 10;

			for (let i = this.planScrollOffset; i < Math.min(visibleEnd, planLines.length); i++) {
				if (i < planLines.length) {
					const line = planLines[i].slice(0, innerWidth - 2);
					lines.push(ansi.border("│") + ` ${line}`.padEnd(innerWidth - 1) + "│");
				}
			}

			if (planLines.length > visibleEnd) {
				const remaining = planLines.length - visibleEnd;
				const indicator = ansi.gray(`… ${remaining} more lines · j/k to scroll`);
				lines.push(ansi.border("│") + ` ${indicator}`.slice(0, innerWidth) + " ".repeat(Math.max(0, innerWidth - indicator.length)) + "│");
			}
		} catch {
			lines.push(ansi.border("│") + ansi.gray(" Failed to read plan file").padEnd(innerWidth) + "│");
		}

		return lines;
	}

	private buildChecklistTab(_task: Task, width: number): string[] {
		const lines: string[] = [];
		const innerWidth = width;
		lines.push(ansi.border("│") + ansi.gray("Checklist: not yet implemented").padEnd(innerWidth) + "│");
		return lines;
	}

	private buildNotesTab(_task: Task, width: number): string[] {
		const lines: string[] = [];
		const innerWidth = width;
		lines.push(ansi.border("│") + ansi.gray("Notes: not yet implemented").padEnd(innerWidth) + "│");
		return lines;
	}

	private getStatusMark(status: string, isSelected: boolean): string {
		const marks: Record<string, string> = {
			in_progress: isSelected ? "▶" : "▶",
			pending: isSelected ? "○" : "○",
			completed: isSelected ? "✓" : "✓",
			failed: isSelected ? "✗" : "✗",
			deferred: isSelected ? "◌" : "◌",
			cancelled: isSelected ? "×" : "×",
		};
		return marks[status] || "•";
	}

	private ensureSelectedVisible(): void {
		const visibleCount = Math.max(0, this.maxViewLines - 4);
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
