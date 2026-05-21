/**
 * Text Utils — ANSI-aware string measurement and padding.
 *
 * Extracted from view/board.ts to isolate the terminal-width
 * measurement logic for testing without ANSI dependencies.
 */

// ---------------------------------------------------------------------------
// Wide character detection (CJK, emoji, etc.)
// ---------------------------------------------------------------------------

export function isWideCodePoint(code: number): boolean {
	return (
		(code >= 0x1100 && code <= 0x115f) ||
		(code >= 0x2329 && code <= 0x232a) ||
		(code >= 0x2e80 && code <= 0xa4cf && code !== 0x303f) ||
		(code >= 0xac00 && code <= 0xd7a3) ||
		(code >= 0xf900 && code <= 0xfaff) ||
		(code >= 0xfe10 && code <= 0xfe19) ||
		(code >= 0xfe30 && code <= 0xfe6f) ||
		(code >= 0xff00 && code <= 0xff60) ||
		(code >= 0xffe0 && code <= 0xffe6)
	);
}

// ---------------------------------------------------------------------------
// ANSI-aware measurement
// ---------------------------------------------------------------------------

/**
 * Calculate the visual width of a string, ignoring ANSI escape codes
 * and counting wide characters as 2 columns.
 */
export function visualWidth(value: string | number): number {
	const str = String(value ?? "");
	let width = 0;
	let inAnsi = false;

	for (let i = 0; i < str.length; i++) {
		if (str[i] === "\x1b") {
			inAnsi = true;
			continue;
		}
		if (inAnsi) {
			if (str[i] === "m") inAnsi = false;
			continue;
		}
		const code = str.codePointAt(i) ?? 0;
		width += isWideCodePoint(code) ? 2 : 1;
	}
	return width;
}

// ---------------------------------------------------------------------------
// ANSI-aware truncation
// ---------------------------------------------------------------------------

/**
 * Truncate a string to fit within `width` visual columns,
 * appending "..." if truncated.
 */
export function truncate(value: string | number, width: number): string {
	const str = String(value ?? "");
	if (visualWidth(str) <= width) return str;

	const suffix = "...";
	const suffixWidth = visualWidth(suffix);
	if (width <= suffixWidth) return suffix.slice(0, width);

	let out = "";
	let w = 0;
	for (const char of str) {
		const cw = visualWidth(char);
		if (w + cw + suffixWidth > width) return out + suffix;
		out += char;
		w += cw;
	}
	return out;
}

// ---------------------------------------------------------------------------
// ANSI-aware padding
// ---------------------------------------------------------------------------

/**
 * Pad a string to `width` visual columns, truncating if necessary.
 */
export function pad(value: string | number, width: number): string {
	const v = truncate(value, width);
	return v + " ".repeat(Math.max(0, width - visualWidth(v)));
}

/**
 * Pad a string to `width` visual columns WITHOUT truncating.
 */
export function padOnly(value: string | number, width: number): string {
	const str = String(value ?? "");
	return str + " ".repeat(Math.max(0, width - visualWidth(str)));
}

// ---------------------------------------------------------------------------
// ANSI strip
// ---------------------------------------------------------------------------

/**
 * Remove ANSI escape codes from a string, leaving only visible text.
 */
export function stripAnsi(value: string): string {
	return value.replace(/\x1b\[[0-9;]*m/g, "");
}