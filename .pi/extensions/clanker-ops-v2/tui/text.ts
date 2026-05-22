// ANSI regex for matching escape sequences
const ANSI_REGEX = /\x1b\[[0-9;]*m/g;

/**
 * Returns true for characters that occupy 2 terminal columns.
 * Covers: CJK Unified Ideographs, Hangul syllables, fullwidth forms,
 * Hiragana, Katakana, and all surrogate pairs (> U+FFFF).
 *
 * East Asian Width "Wide" (W) and "Fullwidth" (F) ranges per Unicode TR#11.
 * We intentionally do NOT include the "Ambiguous" (A) category here —
 * the 1-col safety margin in layout.ts handles those.
 */
function isWideChar(cp: number): boolean {
    if (cp > 0xffff) return true; // Surrogate pairs / supplementary planes
    return (
        (cp >= 0x1100 && cp <= 0x115f) || // Hangul Jamo
        (cp >= 0x2e80 && cp <= 0x303e) || // CJK Radicals, Kangxi, etc.
        (cp >= 0x3040 && cp <= 0x33ff) || // Hiragana, Katakana, Bopomofo, CJK compat
        (cp >= 0x3400 && cp <= 0x4dbf) || // CJK Extension A
        (cp >= 0x4e00 && cp <= 0x9fff) || // CJK Unified Ideographs
        (cp >= 0xa000 && cp <= 0xa4cf) || // Yi Syllables / Radicals
        (cp >= 0xa960 && cp <= 0xa97f) || // Hangul Jamo Extended-A
        (cp >= 0xac00 && cp <= 0xd7af) || // Hangul Syllables  ← 웃 is here
        (cp >= 0xd7b0 && cp <= 0xd7ff) || // Hangul Jamo Extended-B
        (cp >= 0xf900 && cp <= 0xfaff) || // CJK Compatibility Ideographs
        (cp >= 0xfe10 && cp <= 0xfe1f) || // Vertical Forms
        (cp >= 0xfe30 && cp <= 0xfe4f) || // CJK Compatibility Forms
        (cp >= 0xff00 && cp <= 0xff60) || // Fullwidth Latin, punctuation
        (cp >= 0xffe0 && cp <= 0xffe6)    // Fullwidth currency signs
    );
}

export function visualWidth(str: string): number {
    const plain = str.replace(ANSI_REGEX, "");
    let width = 0;
    for (const char of plain) {
        const cp = char.codePointAt(0) || 0;
        width += isWideChar(cp) ? 2 : 1;
    }
    return width;
}


export function truncateToWidth(value: string | number, width: number, suffix = "…"): string {
    const str = String(value);
    const tokens = [];
    let lastIndex = 0;
    let match;

    ANSI_REGEX.lastIndex = 0;
    while ((match = ANSI_REGEX.exec(str)) !== null) {
        if (match.index > lastIndex) {
            tokens.push({ isAnsi: false, text: str.slice(lastIndex, match.index) });
        }
        tokens.push({ isAnsi: true, text: match[0] });
        lastIndex = ANSI_REGEX.lastIndex;
    }
    if (lastIndex < str.length) {
        tokens.push({ isAnsi: false, text: str.slice(lastIndex) });
    }

    let out = "";
    let w = 0;
    let hasAnsi = false;
    const suffixWidth = suffix ? visualWidth(suffix) : 0;

    for (const token of tokens) {
        if (token.isAnsi) {
            out += token.text;
            hasAnsi = true;
        } else {
            let cw = 0;
            let currentText = "";
            for (const char of token.text) {
                const charW = (char.codePointAt(0) || 0) > 0xffff ? 2 : 1;
                if (w + cw + charW + suffixWidth > width) {
                    out += currentText + suffix;
                    if (hasAnsi) out += "\x1b[0m";
                    return out;
                }
                cw += charW;
                currentText += char;
            }
            w += cw;
            out += currentText;
        }
    }
    if (hasAnsi) out += "\x1b[0m";
    return out;
}

export function pad(str: string, width: number): string {
    const vw = visualWidth(str);
    if (vw >= width) {
        return truncateToWidth(str, width, "");
    }
    return str + " ".repeat(width - vw);
}

export const ansi = {
    reset: "\x1b[0m",
    bold: (v: string) => `\x1b[1m${v}\x1b[0m`,
    inverse: "\x1b[7m",
    bgWhite: "\x1b[47m",
    black: "\x1b[30m",
    gray: (v: string) => `\x1b[90m${v}\x1b[0m`,
    red: (v: string) => `\x1b[1;91m${v}\x1b[0m`,
    orange: (v: string) => `\x1b[38;5;214m${v}\x1b[0m`,
    amber: (v: string) => `\x1b[33m${v}\x1b[0m`,
    green: (v: string) => `\x1b[32m${v}\x1b[0m`,
    cyan: (v: string) => `\x1b[36m${v}\x1b[0m`,
    purple: (v: string) => `\x1b[35m${v}\x1b[0m`,
    border: (v: string) => `\x1b[38;5;33m${v}\x1b[0m`,
    accentBg: (v: string) => `\x1b[48;5;236m${v.replace(/\x1b\[0m/g, "\x1b[0m\x1b[48;5;236m")}\x1b[0m`,
};

export function wrapText(str: string, maxWidth: number): string[] {
    const lines: string[] = [];
    const splitByNewline = str.split('\n');
    for (const block of splitByNewline) {
        if (!block.trim()) {
            lines.push("");
            continue;
        }
        
        const words = block.split(' ');
        let currentLine = "";
        
        for (const word of words) {
            if (!currentLine) {
                currentLine = word;
            } else {
                const testLine = currentLine + " " + word;
                if (visualWidth(testLine) <= maxWidth) {
                    currentLine = testLine;
                } else {
                    lines.push(currentLine);
                    currentLine = word;
                }
            }
        }
        if (currentLine) lines.push(currentLine);
    }
    return lines;
}
