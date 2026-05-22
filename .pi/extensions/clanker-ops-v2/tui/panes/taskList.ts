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

        // Format and pad to exact width
        let rowStr = formatTaskRow(task, layout.centerWidth, isSelected);
        rowStr = pad(rowStr, layout.centerWidth);

        // Apply accent highlight for selected row in center pane
        if (isSelected && state.activePane === 'center') {
            rowStr = ansi.accentBg(rowStr);
        }

        lines.push(rowStr);
    }

    // Fill remaining height with blank padded lines
    while (lines.length < height) {
        lines.push(pad("", layout.centerWidth));
    }

    return lines;
}

