/**
 * Scrollable Board Component — TUI Component for a scrollable task board overlay.
 *
 * Implements the TUI Component interface with virtual scrolling:
 * - Renders only visible lines within a max height
 * - Handles up/down arrow keys for navigation
 * - Shows scroll position indicator
 */

import type { Component, TUI } from "@mariozechner/pi-tui";
import { getState } from "../state/store.js";
import type { Task } from "../tool/types.js";

// ---------------------------------------------------------------------------
// ANSI helpers (duplicate from board.ts to avoid circular deps)
// ---------------------------------------------------------------------------

const ansi = {
	gray: (v: string) => `\x1b[90m${v}\x1b[0m`,
	bold: (v: string) => `\x1b[1m${v}\x1b[0m`,
	border: (v: string) => `\x1b[38;5;33m${v}\x1b[0m`,
	amber: (v: string) => `\x1b[33m${v}\x1b[0m`,
};

// ---------------------------------------------------------------------------
// Scrollable Board Component
// ---------------------------------------------------------------------------

export interface ScrollableBoardOptions {
	maxHeight?: number;
	showDone?: boolean;
}

export class ScrollableBoard implements Component {
	private scrollOffset = 0;
	private allLines: string[] = [];
	private maxViewLines: number;
	private tui: TUI | undefined;
	private done: (() => void) | undefined;

	constructor(options: ScrollableBoardOptions = {}) {
		this.maxViewLines = options.maxHeight ?? 20;
	}

	setTUI(tui: TUI): void {
		this.tui = tui;
	}

	setDone(done: () => void): void {
		this.done = done;
	}

	invalidate(): void {
		this.scrollOffset = 0; // Reset scroll on invalidate
	}

	handleInput(data: string): void {
		// Handle arrow keys
		if (data === "\x1b[A") {
			// Up arrow
			this.scrollOffset = Math.max(0, this.scrollOffset - 1);
			this.tui?.requestRender();
		} else if (data === "\x1b[B") {
			// Down arrow
			const maxScroll = Math.max(0, this.allLines.length - this.maxViewLines);
			this.scrollOffset = Math.min(maxScroll, this.scrollOffset + 1);
			this.tui?.requestRender();
		} else if (data === "g" || data === "G") {
			// Jump to top/bottom
			if (data === "g" && this.scrollOffset > 0) {
				this.scrollOffset = 0;
			} else if (data === "G") {
				this.scrollOffset = Math.max(0, this.allLines.length - this.maxViewLines);
			}
			this.tui?.requestRender();
		} else if (data === "q" || data === "\x1b") {
			// Close overlay on q or ESC - hide overlay AND call done() to resolve the promise
			this.tui?.hideOverlay();
			this.done?.();
		}
	}

	render(width: number): string[] {
		// Build all lines from tasks
		this.allLines = this.buildLines(width);

		// Slice for current scroll position
		const visible = this.allLines.slice(
			this.scrollOffset,
			this.scrollOffset + this.maxViewLines
		);

		// Pad if we don't have enough lines
		while (visible.length < this.maxViewLines && visible.length < this.allLines.length) {
			visible.push("");
		}

		// Add scroll indicator if there's more content
		if (this.allLines.length > this.maxViewLines) {
			const totalPages = Math.ceil(this.allLines.length / this.maxViewLines);
			const currentPage = Math.floor(this.scrollOffset / this.maxViewLines) + 1;
			const scrollIndicator = `${ansi.gray("scroll: ")}${ansi.bold(`${currentPage}/${totalPages}`)}`;
			
			// Replace last line with indicator
			if (visible.length > 0) {
				visible[visible.length - 1] = visible[visible.length - 1]
					? `${visible[visible.length - 1]}  ${scrollIndicator}`
					: scrollIndicator;
			}
		}

		return visible.length > 0 ? visible : ["No tasks"];
	}

	private buildLines(width: number): string[] {
		const tasks = this.getVisibleTasks();
		const lines: string[] = [];
		const inner = width - 2;

		// Build bordered board with blue accent
		lines.push(ansi.border(`┌${"─".repeat(inner)}┐`));

		// Title with summary
		const inProgress = tasks.filter(t => t.status === "in_progress").length;
		const pending = tasks.filter(t => t.status === "pending").length;
		const completed = tasks.filter(t => t.status === "completed").length;
		const summary = `${inProgress} active, ${pending} queued, ${completed} done`;
		lines.push(`│ ${ansi.bold("Clanker Ops Board")} ${ansi.gray(`(${summary})`).slice(0, inner - 20).padEnd(inner - 18)} │`);
		lines.push(ansi.border(`├${"─".repeat(inner)}┤`));

		// Column headers
		lines.push(`│ ${ansi.gray("ID").padEnd(5)} ${ansi.gray("Work").padEnd(inner - 18)} ${ansi.gray("Owner")} `.padEnd(inner + 1) + "│");
		lines.push(ansi.border(`├${"─".repeat(inner)}┤`));

		// Active section
		const active = tasks.filter(t => t.status === "in_progress").slice(0, 10);
		for (const t of active) {
			const work = `${t.item}`.slice(0, inner - 20);
			lines.push(`│ #${String(t.id).padStart(3)} ${work.padEnd(inner - 20)} ${(t.assigned || "").padEnd(12)} │`);
		}

		// Reminders
		const dontForget = tasks.filter(t => {
			const tags = t.tags ?? [];
			return tags.some(tag => 
				["remember", "dont-forget", "don't-forget", "chore", "ops"].includes(tag.toLowerCase())
			);
		}).slice(0, 5);
		for (const t of dontForget) {
			const work = `${t.item}`.slice(0, inner - 20);
			lines.push(`│ #${String(t.id).padStart(3)} ${ansi.amber(work.padEnd(inner - 20))} ${(t.assigned || "").padEnd(12)} │`);
		}

		// Queued
		const queued = tasks.filter(t => t.status === "pending" && !dontForget.includes(t)).slice(0, 10);
		for (const t of queued) {
			const work = `${t.item}`.slice(0, inner - 20);
			lines.push(`│ #${String(t.id).padStart(3)} ${work.padEnd(inner - 20)} ${(t.assigned || "").padEnd(12)} │`);
		}

		// Done summary
		if (completed > 0) {
			lines.push(ansi.border(`├${"─".repeat(inner)}┤`));
			lines.push(`│ ${ansi.gray(`✓ ${completed} done — use /clanker all to expand`).slice(0, inner + 1).padEnd(inner + 1)} │`);
		}

		// Controls help
		lines.push(ansi.border(`└${"─".repeat(inner)}┘`));
		lines.push(ansi.gray("[↑↓] scroll  [q/ESC] close"));

		return lines;
	}

	private getVisibleTasks(): Task[] {
		const state = getState();
		return state.tasks.filter(t => t.status !== "deleted");
	}
}