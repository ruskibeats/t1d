/**
 * Board Renderer — ANSI terminal renderer for the Clanker Ops board.
 *
 * Implements a strict 3-pane layout matching reference specifications.
 * All rows are defensively truncated to terminalWidth to preserve layout integrity.
 */

import type { Task } from "../tool/types.js";
import type { BoardTaskViewModel } from "./board-model.js";
import { presentBoard } from "./board-model.js";
import { pad, truncateToWidth, visualWidth } from "./text-utils.js";

// ---------------------------------------------------------------------------
// ANSI helpers
// ---------------------------------------------------------------------------

const ansi = {
	red: (v: string) => `\x1b[1;91m${v}\x1b[0m`,
	orange: (v: string) => `\x1b[38;5;214m${v}\x1b[0m`,
	amber: (v: string) => `\x1b[33m${v}\x1b[0m`,
	green: (v: string) => `\x1b[32m${v}\x1b[0m`,
	cyan: (v: string) => `\x1b[36m${v}\x1b[0m`,
	purple: (v: string) => `\x1b[35m${v}\x1b[0m`,
	border: (v: string) => `\x1b[38;5;33m${v}\x1b[0m`,
	dad: (v: string) => `\x1b[48;5;19m\x1b[38;5;81m${v}\x1b[0m`,
	tom: (v: string) => `\x1b[48;5;34m\x1b[38;5;22m${v}\x1b[0m`,
	gray: (v: string) => `\x1b[90m${v}\x1b[0m`,
	bold: (v: string) => `\x1b[1m${v}\x1b[0m`,
	accentBg: (v: string) => `\x1b[48;5;236m${v.replace(/\x1b\[0m/g, "\x1b[0m\x1b[48;5;236m")}\x1b[0m`, // Dark monochrome accent for selected row
};

function getPaint(paint: string): (v: string) => string {
	switch (paint) {
		case "red": return ansi.red;
		case "orange": return ansi.orange;
		case "amber": return ansi.amber;
		case "green": return ansi.green;
		case "cyan": return ansi.cyan;
		case "purple": return ansi.purple;
		default: return (v) => v;
	}
}

// ---------------------------------------------------------------------------
// Text Wrapping
// ---------------------------------------------------------------------------

function wrapText(text: string | undefined, width: number): string[] {
	if (!text) return [];
	const lines: string[] = [];
	const paragraphs = text.split("\n");
	for (const p of paragraphs) {
		if (p.trim() === "") {
			lines.push("");
			continue;
		}
		const words = p.split(/\s+/);
		let currentLine = "";
		for (const w of words) {
			if (visualWidth(currentLine + (currentLine ? " " : "") + w) <= width) {
				currentLine += (currentLine ? " " : "") + w;
			} else {
				if (currentLine) lines.push(currentLine);
				currentLine = w;
			}
		}
		if (currentLine) lines.push(currentLine);
	}
	return lines;
}

// ---------------------------------------------------------------------------
// Layout Math
// ---------------------------------------------------------------------------

interface LayoutWidths {
	W: number;
	L: number;
	C: number;
	R: number;
}

function calculateWidths(terminalWidth: number): LayoutWidths {
	const W = Math.max(72, terminalWidth);
	const W_in = W - 4; // account for 4 border columns: │ L │ C │ R │
	
	// Left rail is fixed or semi-fixed
	const L = W >= 120 ? 20 : 18;
	
	// Right inspector takes ~30-35% of remaining, min 32, max 40
	let R = Math.floor(W * 0.33);
	if (R > 40) R = 40;
	if (R < 32) R = 32;
	
	// Center takes the rest
	const C = W_in - L - R;
	
	return { W, L, C, R };
}

// ---------------------------------------------------------------------------
// Main render function
// ---------------------------------------------------------------------------

export interface RenderBoardOptions {
	width?: number;
	filter?: Task[];
	includeDone?: boolean;
}

export function renderClankerBoard(
	tasks: readonly Task[],
	options: RenderBoardOptions = {},
): string {
	const terminalWidth = Number(options.width) || Number(process.stdout.columns) || 120;
	const w = calculateWidths(terminalWidth);
	
	const board = presentBoard(tasks);
	const { groups, counts } = board;

	// Identify active task for the right inspector
	const activeTaskVM = groups.active[0] || groups.dontForget[0] || groups.queued[0] || groups.done[0];
	const activeTask = activeTaskVM ? tasks.find(t => t.id === activeTaskVM.id) : undefined;

	// --- 1. Left Rail Lines ---
	const leftRail: string[] = [
		ansi.gray(" BOARDS"),
		` █ Clanker Ops`,
		`   Design system`,
		``,
		ansi.gray(" VIEWS"),
		` █ All Tasks`,
		`   My Tasks`,
		`   Blocked`,
		``,
		ansi.gray(" TAGS")
	];
	
	// Tally tags from actual tasks
	const tagCounts: Record<string, number> = {};
	for (const t of tasks) {
		for (const tag of (t.tags || [])) {
			tagCounts[tag] = (tagCounts[tag] || 0) + 1;
		}
	}
	const sortedTags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]);
	for (const [tag, count] of sortedTags.slice(0, 8)) {
		leftRail.push(`   ${tag} (${count})`);
	}

	// --- 2. Center List Lines ---
	const centerList: string[] = [];
	
	function renderGroup(title: string, vms: readonly BoardTaskViewModel[]) {
		if (vms.length === 0) return;
		const headerLabel = `─ ${title} `;
		const fill = Math.max(0, w.C - visualWidth(headerLabel));
		centerList.push(ansi.border(headerLabel + "─".repeat(fill)));
		
		for (const vm of vms) {
			const isSelected = activeTaskVM && vm.id === activeTaskVM.id;
			const paint = getPaint(vm.paint);
			// Format dense row: " │ ◉  #13 Set up CI/CD pipeline "
			const iconStr = paint(vm.icon);
			const idStr = ansi.gray(`#${vm.id}`);
			const rowStr = ` │ ${iconStr}  ${idStr} ${paint(vm.item)}`;
			const padded = pad(rowStr, w.C);
			centerList.push(isSelected ? ansi.accentBg(padded) : padded);
		}
	}
	
	renderGroup("Active", groups.active);
	renderGroup("Don't Forget", groups.dontForget);
	renderGroup("Queued", groups.queued);
	if (options.includeDone) renderGroup("Completed", groups.done);

	// --- 3. Right Inspector Lines ---
	const rightInspector: string[] = [];
	if (activeTask) {
		rightInspector.push(` Overview  ${ansi.gray("Plan  Edit")}`);
		rightInspector.push(ansi.gray(" ─".repeat(Math.floor(w.R / 2))));
		rightInspector.push(ansi.bold(truncateToWidth(` Task: #${activeTask.id} ${activeTask.item}`, w.R - 1)));
		rightInspector.push(` Status: ${activeTask.status}`);
		rightInspector.push(` Owner: ${activeTask.assigned || "none"}  Priority: ${activeTaskVM?.priorityLevel || "none"}`);
		rightInspector.push(``);
		
		if (activeTask.description) {
			const descLines = wrapText(activeTask.description, w.R - 2);
			for (const line of descLines) {
				rightInspector.push(` ${line}`);
			}
			rightInspector.push(``);
		}
		
		// Simulated plan preview
		rightInspector.push(ansi.gray(` Plan:`));
		if ((activeTask.metadata as any)?.plan) {
			const planLines = wrapText((activeTask.metadata as any).plan, w.R - 2);
			for (const line of planLines.slice(0, 5)) {
				rightInspector.push(` ${line}`);
			}
		} else {
			rightInspector.push(ansi.gray(` (No plan details)`));
		}
	} else {
		rightInspector.push(ansi.gray(" No active task"));
	}

	// --- Combine Panes ---
	const maxLines = Math.max(leftRail.length, centerList.length, rightInspector.length, 5);
	const bodyLines: string[] = [];
	
	for (let i = 0; i < maxLines; i++) {
		const l = leftRail[i] || "";
		const c = centerList[i] || "";
		const r = rightInspector[i] || "";
		
		const line = ansi.border("│") + 
			pad(l, w.L) + ansi.border("│") + 
			pad(c, w.C) + ansi.border("│") + 
			pad(r, w.R) + ansi.border("│");
			
		bodyLines.push(truncateToWidth(line, w.W));
	}

	// --- Header and Footer ---
	const activeCount = groups.active.length;
	const filterText = options.filter ? `Focus: ${options.filter}` : "";
	
	const headerTitle = ` Clanker Ops [${activeCount} Active | ${counts.total} Total]`;
	const searchStrip = `Filter: [ ${filterText} ] `;
	const headerSpacing = Math.max(0, (w.W - 2) - visualWidth(headerTitle) - visualWidth(searchStrip));
	
	const headerInner = pad(headerTitle + " ".repeat(headerSpacing) + searchStrip, w.W - 2);
	const footerInner = pad(` [j/k] Navigate  [P] Plan  [O] Overview  [E] Edit  [q/Esc] Exit`, w.W - 2);
	
	const topBorder = ansi.border("╭" + "─".repeat(w.W - 2) + "╮");
	const headerLine = ansi.border("│") + headerInner + ansi.border("│");
	const splitLine = ansi.border(`├${"─".repeat(w.L)}┬${"─".repeat(w.C)}┬${"─".repeat(w.R)}┤`);
	const botSplit = ansi.border(`├${"─".repeat(w.L)}┼${"─".repeat(w.C)}┼${"─".repeat(w.R)}┤`);
	const footerLine = ansi.border("│") + footerInner + ansi.border("│");
	const botBorder = ansi.border("╰" + "─".repeat(w.W - 2) + "╯");

	// --- Final Assembly ---
	const output = [
		topBorder,
		headerLine,
		splitLine,
		...bodyLines,
		botSplit,
		footerLine,
		botBorder
	];

	return output.join("\n");
}

// ---------------------------------------------------------------------------
// Compact mode — no borders, indentation-based
// ---------------------------------------------------------------------------

export function renderClankerBoardCompact(
	tasks: readonly Task[],
	options: RenderBoardOptions = {},
): string {
	const board = presentBoard(tasks);
	const { groups } = board;
	const inner = options.width ? Math.min(options.width, 100) - 2 : 78;

	const failedCount = tasks.filter((t) => t.status === "failed").length;

	const lines: string[] = [];

	// Build a bordered mini-board with columns
	// Top border (using blue accent)
	lines.push(borderLine("┌", "─".repeat(inner), "┐"));

	// Header with summary
	const summaryParts: string[] = [];
	if (groups.active.length) summaryParts.push(`${groups.active.length} active`);
	if (failedCount) summaryParts.push(ansi.red(`${failedCount} failed`));
	summaryParts.push(`${groups.dontForget.length + groups.queued.length} queued`);
	const summary = summaryParts.join(ansi.gray(" · "));
	const header = ` Clanker Ops`;
	lines.push(box(`${ansi.bold(header)}${" ".repeat(Math.max(1, inner - header.length - summary.length))}${summary}`, inner));
	lines.push(headerRule(inner));

	// Column headers (simplified for widget)
	const colWidths = { id: 5, work: 45, owner: 12 };
	lines.push(
		box(
			row([
				["ID", colWidths.id, ansi.gray],
				["Work", colWidths.work, ansi.gray],
				["Owner", colWidths.owner, ansi.gray],
			]),
			inner,
		),
	);
	lines.push(headerRule(inner));

	// Active tasks (limited to fit widget)
	const activeTasks = groups.active.slice(0, 4);
	for (const vm of activeTasks) {
		const workText = vm.activeForm && vm.status === "in_progress"
			? `${vm.icon} #${vm.id} ${vm.item} (${vm.activeForm})`
			: `${vm.icon} #${vm.id} ${vm.item}`;
		lines.push(
			box(
				row([
					[`#${vm.id}`, colWidths.id, ansi.gray],
					[workText, colWidths.work, getPaint(vm.paint)],
					[vm.owner, colWidths.owner, getOwnerPaint(vm.owner), vm.ownerSpanOnly],
				]),
				inner,
			),
		);
	}

	// Reminders section (limited)
	for (const vm of groups.dontForget.slice(0, 2)) {
		lines.push(
			box(
				row([
					[`#${vm.id}`, colWidths.id, ansi.gray],
					[vm.item, colWidths.work, ansi.amber],
					[vm.owner, colWidths.owner, getOwnerPaint(vm.owner), vm.ownerSpanOnly],
				]),
				inner,
			),
		);
	}

	// Queued (limited)
	for (const vm of groups.queued.slice(0, 3)) {
		lines.push(
			box(
				row([
					[`#${vm.id}`, colWidths.id, ansi.gray],
					[vm.item, colWidths.work, getPaint(vm.paint)],
					[vm.owner, colWidths.owner, getOwnerPaint(vm.owner), vm.ownerSpanOnly],
				]),
				inner,
			),
		);
	}

	// Done summary
	if (groups.done.length) {
		lines.push(headerRule(inner));
		lines.push(box(ansi.gray(` ✓ ${groups.done.length} done`), inner));
	}

	// Bottom border
	lines.push(borderLine("└", "─".repeat(inner), "┘"));

	return lines.join("\n");
}
