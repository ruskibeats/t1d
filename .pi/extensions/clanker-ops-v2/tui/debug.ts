import { UIState, LayoutBudget } from "../state/types.js";
import { pad, ansi } from "./text.js";

export function renderDebugFooter(state: UIState, layout: LayoutBudget): string[] {
    if (!state.debugEnabled) return [];

    const dbgStr = `DEBUG | w:${state.width} h:${state.height} | L:${layout.leftWidth} C:${layout.centerWidth} R:${layout.rightWidth} | active:${state.activePane} tab:${state.activeTab}`;
    // Provide a brightly colored background for debugging visibility
    const padded = pad(dbgStr, layout.totalWidth);
    return [`\x1b[48;5;160m\x1b[37m${padded}\x1b[0m`]; // Red background, white text
}
