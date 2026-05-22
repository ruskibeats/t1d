import { UIState, LayoutBudget } from "../../state/types.js";
import { getInspectorViewModel } from "../../state/selectors.js";
import { pad } from "../text.js";

export function renderInspector(state: UIState, layout: LayoutBudget, height: number): string[] {
    const lines: string[] = [];
    
    // Render a Tab Header at the top of the right pane
    const tabHeader = 
        state.activeTab === 'overview' ? "[O] OVERVIEW  [P] Plan  [E] Edit" :
        state.activeTab === 'plan'     ? "[O] Overview  [P] PLAN  [E] Edit" :
                                         "[O] Overview  [P] Plan  [E] EDIT";
    
    // Add the tab header as the first line (always visible)
    lines.push(" " + pad(tabHeader, layout.rightWidth - 1));
    lines.push(" " + pad("─".repeat(layout.rightWidth - 2), layout.rightWidth - 1));

    // Get pre-formatted view model content
    const vm = getInspectorViewModel(state);
    
    // Apply scrolling
    const visibleContent = vm.inspectorContent.slice(state.inspectorScrollOffset, state.inspectorScrollOffset + height - 2);
    
    for (const line of visibleContent) {
        lines.push(" " + pad(line, layout.rightWidth - 1));
    }
    
    // Fill the rest of the height
    while (lines.length < height) {
        lines.push(pad("", layout.rightWidth));
    }
    
    return lines;
}
