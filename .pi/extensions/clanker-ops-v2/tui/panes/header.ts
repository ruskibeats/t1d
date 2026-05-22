import { UIState, LayoutBudget } from "../../state/types.js";
import { pad, ansi, visualWidth } from "../text.js";

export function renderTopBorder(layout: LayoutBudget): string {
    return ansi.border("╭" + "─".repeat(layout.totalWidth - 2) + "╮");
}

export function renderHeader(state: UIState, layout: LayoutBudget): string {
    const activeCount = state.tasks.filter(t => t.status === "in_progress" || t.status === "todo").length;
    const totalCount = state.tasks.length;
    
    const headerTitle = ` Clanker Ops [${activeCount} Active | ${totalCount} Total]`;
    const filterText = state.searchQuery ? `Focus: ${state.searchQuery}` : "";
    const searchStrip = `Filter: [ ${filterText} ] `;

    const headerInnerWidth = layout.totalWidth - 2;
    const headerSpacing = Math.max(0, headerInnerWidth - visualWidth(headerTitle) - visualWidth(searchStrip));
    const headerInner = pad(headerTitle + " ".repeat(headerSpacing) + searchStrip, headerInnerWidth);

    return ansi.border("│") + headerInner + ansi.border("│");
}

export function renderHeaderSeparator(layout: LayoutBudget): string {
    const L = "─".repeat(layout.leftWidth);
    const C = "─".repeat(layout.centerWidth);
    const R = "─".repeat(layout.rightWidth);
    return ansi.border(`├${L}┬${C}┬${R}┤`);
}
