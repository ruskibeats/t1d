import { UIState, LayoutBudget } from "../../state/types.js";
import { pad, ansi } from "../text.js";

export function renderLeftRail(state: UIState, layout: LayoutBudget, height: number): string[] {
    const lines: string[] = [];
    
    // Items: 0=Main Ops, 1=Backend, 2=All Active, 3=ui (3)
    // We don't have true list data yet, so hardcode the active index logic
    const highlight = (text: string, index: number) => {
        const isSelected = state.leftActiveIndex === index;
        const prefix = isSelected ? " > " : "   ";
        const content = isSelected ? ansi.bold(text) : text;
        const line = prefix + content;
        return isSelected && state.activePane === 'left' ? ansi.accentBg(line) : line;
    };

    lines.push(" BOARDS");
    lines.push(highlight("Main Ops", 0));
    lines.push(highlight("Backend", 1));
    lines.push("");
    lines.push(" VIEWS");
    lines.push(highlight("All Active", 2));
    
    const assignedLabel = state.assignedFilterOwner ? `Assigned [${state.assignedFilterOwner}]` : "Assigned [Any]";
    lines.push(highlight(assignedLabel, 3));
    
    lines.push(highlight("Completed", 4));
    lines.push("");
    lines.push(" TAGS");
    lines.push(highlight("ui (3)", 5));
    
    // Pad all generated lines
    const paddedLines = lines.map(line => pad(line, layout.leftWidth));
    
    // Fill the rest of the height with empty padded lines
    while (paddedLines.length < height) {
        paddedLines.push(pad("", layout.leftWidth));
    }
    
    // If it exceeds height (unlikely for static content), slice it
    return paddedLines.slice(0, height);
}
