import { LayoutBudget } from "../state/types.js";

// Primary design target is 100 columns. Upscale to 120 if possible.
export function calculateLayout(terminalWidth: number): LayoutBudget {
    // We subtract 5 (4 borders + 1 safety margin) rather than 4.
    //
    // WHY THE SAFETY MARGIN: East Asian Width "Ambiguous" Unicode characters
    // (em dash —, curly quotes '', geometric shapes, etc.) are measured as
    // 1-wide by our simple visualWidth() heuristic, but are rendered as
    // 2-wide by the pi terminal runtime. A single ambiguous char anywhere in
    // a line will make the line 1 column wider than we calculated, causing
    // the "Rendered line exceeds terminal width" crash. Using effectiveWidth =
    // terminalWidth - 1 provides a 1-char buffer so this never triggers.
    const effectiveWidth = terminalWidth - 1;
    const usableWidth    = effectiveWidth - 4; // 4 vertical border chars │

    if (terminalWidth >= 120) {
        return {
            leftWidth:   23,
            centerWidth: usableWidth - 23 - 34,
            rightWidth:  34,
            totalWidth:  effectiveWidth,
        };
    } else if (terminalWidth >= 100) {
        const diff = terminalWidth - 100;
        const left  = 19 + Math.floor(diff * 0.2);
        const right = 49 + Math.floor(diff * 0.5);
        return {
            leftWidth:   left,
            centerWidth: usableWidth - left - right,
            rightWidth:  right,
            totalWidth:  effectiveWidth,
        };
    } else {
        // Sub-100 fallback
        const left  = Math.max(13, Math.floor(usableWidth * 0.19));
        const right = Math.max(16, Math.floor(usableWidth * 0.28));
        return {
            leftWidth:   left,
            centerWidth: usableWidth - left - right,
            rightWidth:  right,
            totalWidth:  effectiveWidth,
        };
    }
}

