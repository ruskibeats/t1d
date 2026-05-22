import { renderClankerBoardV2 } from "./tui/render.js";
import { UIState } from "./state/types.js";
import { loadTasks } from "./state/loadTasks.js";

const state: UIState = {
    width: 100,
    height: 25,
    tasks: loadTasks(),
    activeIndex: 1, // select the second task to show accent bg
    activePane: 'center',
    activeTab: 'overview',
    activeBoard: 'Main Ops',
    searchQuery: '',
    listScrollOffset: 0,
    inspectorScrollOffset: 0,
    debugEnabled: true
};

const lines = renderClankerBoardV2(state);
for (const line of lines) {
    // We print the raw output. To make it legible in a basic log, 
    // we might need to strip ANSI, but let's see it with ANSI first.
    console.log(line.replace(/\x1b\[[0-9;]*m/g, ''));
}
