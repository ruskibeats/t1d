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

	constructor(options: ScrollableBoardOptions = {}) {
		this.maxViewLines = options.maxHeight ?? 20;
	}

	setTUI(tui: TUI): void {
		this.tui = tui;
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
			// Close overlay on q or ESC
			this.tui?.hideOverlay();
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

		// Header
		const title = ` Clanker Ops Board`;
		lines.push(title);

		// Tasks grouped by status
		const inProgress = tasks.filter(t => t.status === "in_progress");
		const pending = tasks.filter(t => t.status === "pending");
		const completed = tasks.filter(t => t.status === "completed");
		const dontForget = tasks.filter(t => {
			const tags = t.tags ?? [];
			return tags.some(tag => 
				["remember", "dont-forget", "don't-forget", "chore", "ops"].includes(tag.toLowerCase())
			);
		});

		// Active section
		if (inProgress.length > 0) {
			lines.push("");
			lines.push("Active:");
			for (const t of inProgress) {
				const owner = t.assigned ? ` @${t.assigned}` : "";
				const active = t.activeForm ? ` (${t.activeForm})` : "";
				lines.push(`  ◐ #${t.id} ${t.item}${active}${owner}`);
			}
		}

		// Reminders section
		if (dontForget.length > 0) {
			lines.push("");
			lines.push("Reminders:");
			for (const t of dontForget) {
				lines.push(`  ! #${t.id} ${t.item}`);
			}
		}

		// Queued section
		if (pending.length > 0) {
			lines.push("");
			lines.push("Queued:");
			for (const t of pending) {
				const owner = t.assigned ? ` @${t.assigned}` : "";
				lines.push(`  ○ #${t.id} ${t.item}${owner}`);
			}
		}

		// Completed section - summary only
		if (completed.length > 0) {
			lines.push("");
			lines.push(`✓ ${completed.length} done — use /clanker all to expand`);
		}

		// Controls help
		if (lines.length > 0) {
			lines.push("");
			lines.push(ansi.gray("[↑↓] scroll  [q/ESC] close"));
		}

		return lines;
	}

	private getVisibleTasks(): Task[] {
		const state = getState();
		return state.tasks.filter(t => t.status !== "deleted");
	}
}