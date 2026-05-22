import { UIState } from "../state/types.js";
import { calculateLayout } from "./layout.js";
import { truncateToWidth, ansi } from "./text.js";
import { renderHeader, renderHeaderSeparator, renderTopBorder } from "./panes/header.js";
import { renderLeftRail } from "./panes/leftRail.js";
import { renderTaskList } from "./panes/taskList.js";
import { renderInspector } from "./panes/inspector.js";
import { renderFooter, renderFooterSeparator, renderBottomBorder } from "./panes/footer.js";
import { renderDebugFooter } from "./debug.js";

export function renderClankerBoardV2(state: UIState): string[] {
    const layout = calculateLayout(state.width);
    
    const debugHeight = state.debugEnabled ? 1 : 0;
    const topMarginHeight = 5;
    const reservedHeight = 6 + debugHeight + topMarginHeight;
    const bodyHeight = Math.max(1, state.height - reservedHeight);

    const leftPane = renderLeftRail(state, layout, bodyHeight);
    const centerPane = renderTaskList(state, layout, bodyHeight);
    const rightPane = renderInspector(state, layout, bodyHeight);

    const out: string[] = [];

    const logoLines = [
        ansi.cyan("▗▄▄▖▗▖    ▗▄▖ ▗▖  ▗▖▗▖ ▗▖▗▄▄▄▖▗▄▄▖      ▗▄▖ ▗▄▄▖  ▗▄▄▖"),
        ansi.cyan("▐▌   ▐▌   ▐▌ ▐▌▐▛▚▖▐▌▐▌▗▞▘▐▌   ▐▌ ▐▌    ▐▌ ▐▌▐▌ ▐▌▐▌   "),
        ansi.cyan("▐▌   ▐▌   ▐▛▀▜▌▐▌ ▝▜▌▐▛▚▖ ▐▛▀▀▘▐▛▀▚▖    ▐▌ ▐▌▐▛▀▘  ▝▀▚▖"),
        ansi.cyan("▝▚▄▄▖▐▙▄▄▖▐▌ ▐▌▐▌  ▐▌▐▌ ▐▌▐▙▄▄▖▐▌ ▐▌    ▝▚▄▞▘▐▌   ▗▄▄▞▘")
    ];

    for (let i = 0; i < topMarginHeight; i++) {
        if (i < logoLines.length) {
            out.push(logoLines[i]);
        } else {
            out.push("");
        }
    }

    out.push(truncateToWidth(renderTopBorder(layout), state.width, ""));
    out.push(truncateToWidth(renderHeader(state, layout), state.width, ""));
    out.push(truncateToWidth(renderHeaderSeparator(layout), state.width, ""));

    for (let i = 0; i < bodyHeight; i++) {
        const row = ansi.border("│") + leftPane[i] + ansi.border("│") + centerPane[i] + ansi.border("│") + rightPane[i] + ansi.border("│");
        out.push(truncateToWidth(row, state.width, ""));
    }

    out.push(truncateToWidth(renderFooterSeparator(layout), state.width, ""));
    out.push(truncateToWidth(renderFooter(state, layout), state.width, ""));
    out.push(truncateToWidth(renderBottomBorder(layout), state.width, ""));

    // Debug
    if (state.debugEnabled) {
        const debugLines = renderDebugFooter(state, layout);
        for (const line of debugLines) {
            out.push(truncateToWidth(line, state.width, ""));
        }
    }

    return out;
}
