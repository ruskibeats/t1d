import { UIState, LayoutBudget } from "../../state/types.js";
import { pad, ansi, truncateToWidth } from "../text.js";
import { getInspectorViewModel } from "../../state/selectors.js";

export function renderInspector(state: UIState, layout: LayoutBudget, height: number): string[] {
    const lines: string[] = [];
    const W = layout.rightWidth;

    // Tab header matching the static /clanker board style
    const tabO = state.activeTab === 'overview' ? ansi.bold(" [O] OVERVIEW") : ansi.gray(" [O] Overview");
    const tabP = state.activeTab === 'plan'     ? ansi.bold(" [P] PLAN")     : ansi.gray(" [P] Plan");
    const tabE = state.activeTab === 'edit'     ? ansi.bold(" [E] EDIT")     : ansi.gray(" [E] Edit");
    const tabHeader = tabO + tabP + tabE;
    lines.push(pad(tabHeader, W));

    // Separator
    lines.push(ansi.gray(" " + "─".repeat(Math.max(0, W - 2))));

    // Content from view model
    const vm = getInspectorViewModel(state, W - 2);
    const visibleContent = vm.inspectorContent.slice(
        state.inspectorScrollOffset,
        state.inspectorScrollOffset + height - 2
    );

    for (const line of visibleContent) {
        lines.push(pad(" " + truncateToWidth(line, W - 2, ""), W));
    }

    // Fill the rest of the height
    while (lines.length < height) {
        lines.push(pad("", W));
    }

    return lines.slice(0, height);
}

