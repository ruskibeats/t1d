import { UIState, LayoutBudget } from "../../state/types.js";
import { pad, ansi } from "../text.js";

export function renderLeftRail(state: UIState, layout: LayoutBudget, height: number): string[] {
    const lines: string[] = [];
    
    // Add static left rail content for v1
    lines.push(" BOARDS");
    lines.push(state.activeBoard === "Main Ops" ? ansi.bold(" > Main Ops") : "   Main Ops");
    lines.push("   Backend");
    lines.push("");
    lines.push(" VIEWS");
    lines.push(ansi.bold(" > All Active"));
    lines.push("   Assigned");
    lines.push("   Completed");
    lines.push("");
    lines.push(" TAGS");
    lines.push("   ui (3)");
    
    // Pad all generated lines
    const paddedLines = lines.map(line => pad(line, layout.leftWidth));
    
    // Fill the rest of the height with empty padded lines
    while (paddedLines.length < height) {
        paddedLines.push(pad("", layout.leftWidth));
    }
    
    // If it exceeds height (unlikely for static content), slice it
    return paddedLines.slice(0, height);
}
