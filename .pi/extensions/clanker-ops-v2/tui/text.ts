// ANSI regex for matching escape sequences
const ANSI_REGEX = /\x1b\[[0-9;]*m/g;

export function visualWidth(str: string): number {
    const plain = str.replace(ANSI_REGEX, "");
    let width = 0;
    for (const char of plain) {
        width += (char.codePointAt(0) || 0) > 0xffff ? 2 : 1;
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
