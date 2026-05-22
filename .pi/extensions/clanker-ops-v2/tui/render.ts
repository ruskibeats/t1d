import { UIState } from "../state/types.js";
import { calculateLayout } from "./layout.js";
import { truncateToWidth } from "./text.js";
import { renderHeader, renderHeaderSeparator } from "./panes/header.js";
import { renderLeftRail } from "./panes/leftRail.js";
import { renderTaskList } from "./panes/taskList.js";
import { renderInspector } from "./panes/inspector.js";
import { renderFooter, renderFooterSeparator } from "./panes/footer.js";
import { renderDebugFooter } from "./debug.js";

export function renderClankerBoardV2(state: UIState): string[] {
    const layout = calculateLayout(state.width);
    
    // We reserve 1 line for header, 1 for header-sep, 1 for footer-sep, 1 for footer
    // That's 4 static structural lines. We add 1 extra line (so 5 total) to prevent terminal scroll.
    // Plus debug footer if enabled (1 line).
    const debugHeight = state.debugEnabled ? 1 : 0;
    const reservedHeight = 5 + debugHeight;
    const bodyHeight = Math.max(1, state.height - reservedHeight);

    // Render individual panes
    const leftPane = renderLeftRail(state, layout, bodyHeight);
    const centerPane = renderTaskList(state, layout, bodyHeight);
    const rightPane = renderInspector(state, layout, bodyHeight);

    const out: string[] = [];

    // Header
    out.push(truncateToWidth(renderHeader(state, layout), state.width, ""));
    out.push(truncateToWidth(renderHeaderSeparator(layout), state.width, ""));

    // Body Composition
    for (let i = 0; i < bodyHeight; i++) {
        const row = `${leftPane[i]}│${centerPane[i]}│${rightPane[i]}`;
        out.push(truncateToWidth(row, state.width, ""));
    }

    // Footer
    out.push(truncateToWidth(renderFooterSeparator(layout), state.width, ""));
    out.push(truncateToWidth(renderFooter(state, layout), state.width, ""));

    // Debug
    if (state.debugEnabled) {
        const debugLines = renderDebugFooter(state, layout);
        for (const line of debugLines) {
            out.push(truncateToWidth(line, state.width, ""));
        }
    }

    return out;
}
