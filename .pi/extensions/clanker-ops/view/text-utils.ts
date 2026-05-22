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
 * appending "..." if truncated. Preserves complete ANSI sequences
 * and emits a reset at the end if truncated.
 */
export function truncateToWidth(value: string | number, width: number): string {
	const str = String(value ?? "");
	if (visualWidth(str) <= width) return str;

	const suffix = "...";
	const suffixWidth = 3;
	if (width <= suffixWidth) return suffix.slice(0, width);

	const ansiRegex = /\x1b\[[0-9;]*m/g;
	let match;
	let lastIndex = 0;
	let out = "";
	let w = 0;
	let hasAnsi = false;

	const tokens: {text: string, isAnsi: boolean}[] = [];
	ansiRegex.lastIndex = 0;
	while ((match = ansiRegex.exec(str)) !== null) {
		if (match.index > lastIndex) {
			tokens.push({ text: str.slice(lastIndex, match.index), isAnsi: false });
		}
		tokens.push({ text: match[0], isAnsi: true });
		lastIndex = ansiRegex.lastIndex;
	}
	if (lastIndex < str.length) {
		tokens.push({ text: str.slice(lastIndex), isAnsi: false });
	}

	for (const token of tokens) {
		if (token.isAnsi) {
			out += token.text;
			hasAnsi = true;
		} else {
			for (const char of token.text) {
				const cw = visualWidth(char);
				if (w + cw + suffixWidth > width) {
					out += suffix;
					if (hasAnsi) out += "\x1b[0m";
					return out;
				}
				out += char;
				w += cw;
			}
		}
	}
	
	if (hasAnsi) out += "\x1b[0m";
	return out;
}

// Keep export for backward compatibility if needed, or point to truncateToWidth
export const truncate = truncateToWidth;

// ---------------------------------------------------------------------------
// ANSI-aware padding
// ---------------------------------------------------------------------------

/**
 * Pad a string to `width` visual columns, truncating if necessary.
 */
export function pad(value: string | number, width: number): string {
	const v = truncateToWidth(value, width);
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