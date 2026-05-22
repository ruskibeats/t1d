import { LayoutBudget } from "../state/types.js";

// Primary design target is 100 columns. Upscale to 120 if possible.
export function calculateLayout(terminalWidth: number): LayoutBudget {
    // We need 4 columns for separators/borders: `│ Left │ Center │ Right │`
    // Let's assume inner separators only if we don't have outer borders.
    // The spec says: "The layout uses 4 vertical borders (│), meaning the sum of pane widths plus 4 must exactly equal the total width."

    const usableWidth = terminalWidth - 4;

    if (terminalWidth >= 120) {
        return {
            leftWidth: 20,
            centerWidth: usableWidth - 20 - 44, // 52
            rightWidth: 44,
            totalWidth: terminalWidth
        };
    } else if (terminalWidth >= 100) {
        // Degrade gracefully between 100 and 120
        const diff = terminalWidth - 100;
        return {
            leftWidth: 16 + Math.floor(diff * 0.2),
            centerWidth: 42 + Math.floor(diff * 0.5),
            rightWidth: usableWidth - (16 + Math.floor(diff * 0.2)) - (42 + Math.floor(diff * 0.5)),
            totalWidth: terminalWidth
        };
    } else {
        // Sub-100 fallback (try to keep composition, shrink heavily)
        const left = Math.max(10, Math.floor(usableWidth * 0.16));
        const right = Math.max(26, Math.floor(usableWidth * 0.38));
        return {
            leftWidth: left,
            centerWidth: usableWidth - left - right,
            rightWidth: right,
            totalWidth: terminalWidth
        };
    }
}
