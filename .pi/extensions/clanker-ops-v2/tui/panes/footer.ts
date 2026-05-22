import { UIState, LayoutBudget } from "../../state/types.js";
import { pad } from "../text.js";

export function renderFooter(state: UIState, layout: LayoutBudget): string {
    const hints = " [Tab] Pane  [↑/↓] Move  [O] Overview  [P] Plan  [E] Edit  [d] Toggle Debug ";
    return pad(hints, layout.totalWidth);
}

export function renderFooterSeparator(layout: LayoutBudget): string {
    const L = "─".repeat(layout.leftWidth);
    const C = "─".repeat(layout.centerWidth);
    const R = "─".repeat(layout.rightWidth);
    return `${L}┴${C}┴${R}`;
}
