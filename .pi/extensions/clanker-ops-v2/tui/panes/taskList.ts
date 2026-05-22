import { UIState, LayoutBudget } from "../../state/types.js";
import { formatTaskRow, getFilteredTasks } from "../../state/selectors.js";
import { pad, ansi } from "../text.js";

export function renderTaskList(state: UIState, layout: LayoutBudget, height: number): string[] {
    const lines: string[] = [];
    
    const filteredTasks = getFilteredTasks(state);
    const visibleTasks = filteredTasks.slice(state.listScrollOffset, state.listScrollOffset + height);
    
    for (let i = 0; i < visibleTasks.length; i++) {
        const globalIndex = state.listScrollOffset + i;
        const task = visibleTasks[i];
        
        const isSelected = globalIndex === state.activeIndex;
        
        // 1. Format the row using selectors
        let rowStr = formatTaskRow(task, layout.centerWidth - 1, isSelected);
        
        // 2. Pad to exact width
        rowStr = " " + pad(rowStr, layout.centerWidth - 1);
        
        // 3. Apply accent styling if selected
        if (isSelected && state.activePane === 'center') {
            rowStr = ansi.accentBg(rowStr);
        }
        
        lines.push(rowStr);
    }
    
    // Fill the rest of the height with empty padded lines
    while (lines.length < height) {
        lines.push(pad("", layout.centerWidth));
    }
    
    return lines;
}
