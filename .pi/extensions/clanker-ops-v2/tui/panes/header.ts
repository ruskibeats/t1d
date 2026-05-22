import { UIState, LayoutBudget } from "../../state/types.js";
import { pad, ansi } from "../text.js";

export function renderHeader(state: UIState, layout: LayoutBudget): string {
    const leftText = " CLANKER OPS ";
    const centerText = ` FILTER: ${state.searchQuery || "Type to filter..."}`;
    const rightText = " (Esc clears / q quits) ";

    let L = pad(leftText, layout.leftWidth);
    let C = pad(centerText, layout.centerWidth);
    let R = pad(rightText, layout.rightWidth);

    if (state.activePane === 'left') L = ansi.accentBg(L);
    if (state.activePane === 'center') C = ansi.accentBg(C);
    if (state.activePane === 'right') R = ansi.accentBg(R);

    // Join with vertical separators
    const row = `${L}│${C}│${R}`;
    
    // Invert colors for header (simulated by bold or bg)
    return ansi.bold(row);
}

export function renderHeaderSeparator(layout: LayoutBudget): string {
    const L = "─".repeat(layout.leftWidth);
    const C = "─".repeat(layout.centerWidth);
    const R = "─".repeat(layout.rightWidth);
    return `${L}┼${C}┼${R}`;
}
