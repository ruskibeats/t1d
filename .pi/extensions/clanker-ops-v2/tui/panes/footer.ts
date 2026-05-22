import { UIState, LayoutBudget } from "../../state/types.js";
import { pad, ansi } from "../text.js";

export function renderFooter(state: UIState, layout: LayoutBudget): string {
    const hints = " [Tab] Pane  [↑/↓] Move  [O] Overview  [P] Plan  [E] Edit  [q/Esc] Exit ";
    const footerInner = pad(hints, layout.totalWidth - 2);
    return ansi.border("│") + footerInner + ansi.border("│");
}

export function renderFooterSeparator(layout: LayoutBudget): string {
    const L = "─".repeat(layout.leftWidth);
    const C = "─".repeat(layout.centerWidth);
    const R = "─".repeat(layout.rightWidth);
    return ansi.border(`├${L}┼${C}┼${R}┤`);
}

export function renderBottomBorder(layout: LayoutBudget): string {
    return ansi.border("╰" + "─".repeat(layout.totalWidth - 2) + "╯");
}
