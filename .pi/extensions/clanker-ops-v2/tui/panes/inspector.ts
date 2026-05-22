import { UIState, LayoutBudget } from "../../state/types.js";
import { getInspectorViewModel } from "../../state/selectors.js";
import { pad } from "../text.js";

export function renderInspector(state: UIState, layout: LayoutBudget, height: number): string[] {
    const lines: string[] = [];
    
    // Get pre-formatted view model content
    const vm = getInspectorViewModel(state);
    
    // Apply scrolling
    const visibleContent = vm.inspectorContent.slice(state.inspectorScrollOffset, state.inspectorScrollOffset + height);
    
    for (const line of visibleContent) {
        lines.push(" " + pad(line, layout.rightWidth - 1));
    }
    
    // Fill the rest of the height
    while (lines.length < height) {
        lines.push(pad("", layout.rightWidth));
    }
    
    return lines;
}
