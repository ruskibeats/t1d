import { UIState, LayoutBudget } from "../../state/types.js";
import { pad, ansi, truncateToWidth } from "../text.js";

export function renderLeftRail(state: UIState, layout: LayoutBudget, height: number): string[] {
    const lines: string[] = [];
    const W = layout.leftWidth;

    const highlight = (text: string, index: number) => {
        const isSelected = state.leftActiveIndex === index;
        const prefix = isSelected ? " █ " : "   ";
        const content = isSelected ? ansi.bold(text) : text;
        const line = prefix + truncateToWidth(content, W - 3, "…");
        return isSelected && state.activePane === "left" ? ansi.accentBg(line) : line;
    };

    // --- BOARDS ---
    lines.push(ansi.gray(" BOARDS"));
    lines.push(highlight("Main Ops", 0));
    lines.push(highlight("Backend", 1));
    lines.push("");

    // --- VIEWS ---
    lines.push(ansi.gray(" VIEWS"));
    lines.push(highlight("All Active", 2));
    lines.push(highlight("Completed", 3));

    // When an owner filter is active, show just "[owner]" (compact) rather than
    // "Assigned [owner]" which overflows the 23-col pane for long usernames.
    const assignedLabel = state.assignedFilterOwner
        ? `[${state.assignedFilterOwner}]`
        : "Assigned [Any]";
    lines.push(highlight(assignedLabel, 4));
    lines.push("");

    // --- TAGS (dynamic from actual tasks) ---
    lines.push(ansi.gray(" TAGS"));
    const tagCounts: Record<string, number> = {};
    for (const t of state.tasks) {
        for (const tag of (t.tags || [])) {
            tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        }
    }
    const sortedTags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]);
    let tagIndex = 5;
    for (const [tag, count] of sortedTags.slice(0, 8)) {
        lines.push(highlight(`${tag} (${count})`, tagIndex++));
    }

    // Pad & slice
    const paddedLines = lines.map(line => pad(line, W));
    while (paddedLines.length < height) {
        paddedLines.push(pad("", W));
    }
    return paddedLines.slice(0, height);
}

