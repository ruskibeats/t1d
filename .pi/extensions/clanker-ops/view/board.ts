/**
 * Board Renderer — ANSI terminal renderer for the Clanker Ops board.
 *
 * Pure rendering: accepts task data, produces ANSI strings.
 * No file I/O, no side effects — all data is passed in.
 *
 * Business logic (classification, grouping) lives in board-model.ts.
 * Text measurement utilities live in text-utils.ts.
 */

import type { Task } from "../tool/types.js";
import type { BoardTaskViewModel } from "./board-model.js";
import { presentBoard, computeColumnWidths } from "./board-model.js";
import { pad, padOnly } from "./text-utils.js";

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
};

// ---------------------------------------------------------------------------
// Paint helpers
// ---------------------------------------------------------------------------

function getPaint(paint: string): (v: string) => string {
	switch (paint) {
		case "red":
			return ansi.red;
		case "orange":
			return ansi.orange;
		case "amber":
			return ansi.amber;
		case "green":
			return ansi.green;
		case "cyan":
			return ansi.cyan;
		case "purple":
			return ansi.purple;
		default:
			return (v) => v;
	}
}

function getOwnerPaint(owner: string): (v: string) => string {
	if (owner === "@dad_웃" || owner === "dad_웃") return ansi.dad;
	if (owner === "@tom_웃" || owner === "tom_웃") return ansi.tom;
	if (owner.includes("웃")) return ansi.cyan;
	return ansi.gray;
}

function getTagPaint(vm: BoardTaskViewModel): (v: string) => string {
	return (v: string) => {
		if (vm.priorityLevel === "p0") return ansi.red(v);
		if (vm.priorityLevel === "p1") return ansi.orange(v);
		if (vm.priorityLevel === "p2") return ansi.green(v);
		return ansi.gray(v);
	};
}

function getPlanPaint(vm: BoardTaskViewModel): (v: string) => string {
	if (vm.planRef === "missing" && vm.status !== "completed") return ansi.orange;
	return ansi.gray;
}

function getLastPaint(vm: BoardTaskViewModel): (v: string) => string {
	if (vm.lastRan !== "-") return ansi.green;
	return ansi.gray;
}

// ---------------------------------------------------------------------------
// Cell rendering
// ---------------------------------------------------------------------------

type Column = [value: string, width: number];

function row(cells: Array<[string, number, (v: string) => string, boolean?]>): string {
	return ` ${cells
		.map(([value, w, paint, spanOnly = false]) => {
			if (!spanOnly) return paint(pad(value, w));
			const plain = pad(value, w);
			return paint(plain);
		})
		.join(" ")} `;
}

function borderLine(left: string, fill: string, right: string): string {
	return `${left}${ansi.border(`${fill}${right}`)}`;
}

function box(content: string, inner: number): string {
	return `│${padOnly(content, inner)}${ansi.border("│")}`;
}

function headerRule(inner: number): string {
	return borderLine("├", "─".repeat(inner), "┤");
}

function sectionHeader(name: string, inner: number): string[] {
	const label = `─ ${name} `;
	return [
		borderLine("├", `${label}${"─".repeat(Math.max(1, inner - label.length))}`, "┤"),
	];
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
	const width = Math.max(
		72,
		Math.min(Number(options.width) || Number(process.stdout.columns) || 120, 140),
	);
	const inner = width - 2;
	const cols = computeColumnWidths(inner);

	const board = presentBoard(tasks);
	const { groups, counts, summary } = board;

	const filterText = options.filter ? ` [Focus: ${options.filter}]` : "";
	const title = ` Clanker Ops${filterText}`;

	// Sub-table renderer
	function addGroup(name: string, group: readonly BoardTaskViewModel[]): string[] {
		if (!group.length) return [];
		const lines = sectionHeader(name, inner);
		for (const vm of group) {
			lines.push(
				box(
					row([
						[vm.icon, cols.icon, getPaint(vm.paint)],
						[`#${vm.id}`, cols.id, ansi.gray],
						[vm.item, cols.work, getPaint(vm.paint)],
						[vm.owner, cols.owner, getOwnerPaint(vm.owner), vm.ownerSpanOnly],
						[vm.tags, cols.tags, getTagPaint(vm)],
						[vm.planRef === "exists" ? "yes" : vm.planRef, cols.plan, getPlanPaint(vm)],
						[vm.lastRan, cols.last, getLastPaint(vm)],
					]),
					inner,
				),
			);
		}
		return lines;
	}

	const lines: string[] = [];

	// Top border + title
	lines.push(borderLine("╭", "─".repeat(inner), "╮"));
	lines.push(box(`${ansi.bold(title)}${" ".repeat(Math.max(1, inner - title.length))}${ansi.gray(summary)}`, inner));
	lines.push(headerRule(inner));

	// Column headers
	lines.push(
		box(
			row([
				["", cols.icon, ansi.gray],
				["ID", cols.id, ansi.gray],
				["Work", cols.work, ansi.gray],
				["Owner", cols.owner, ansi.gray],
				["Tags", cols.tags, ansi.gray],
				["Plan", cols.plan, ansi.gray],
				["Last", cols.last, ansi.gray],
			]),
			inner,
		),
	);
	lines.push(headerRule(inner));

	// Groups
	lines.push(...addGroup("Active", groups.active));
	lines.push(...addGroup("Don't Forget", groups.dontForget));
	lines.push(...addGroup("Queued", groups.queued));

	if (options.includeDone && groups.done.length) {
		lines.push(...addGroup("Completed", groups.done));
	} else if (groups.done.length) {
		lines.push(...sectionHeader("Done", inner));
		lines.push(box(ansi.gray(` ✓ ${groups.done.length} done; use --all to show them`), inner));
	}

	// Legend
	lines.push(headerRule(inner));
	lines.push(
		box(
			[
				ansi.red("red fail/p0"),
				ansi.orange("orange p1/no-plan"),
				ansi.amber("amber reminder"),
				ansi.green("green p2"),
				ansi.cyan("cyan blocked"),
				ansi.purple("purple dupe"),
			].join(ansi.gray(" · ")),
			inner,
		),
	);
	lines.push(borderLine("╰", "─".repeat(inner), "╯"));

	return lines.join("\n");
}
