import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { UIState } from "./state/types.js";
import { loadTasks } from "./state/loadTasks.js";
import { renderClankerBoardV2 } from "./tui/render.js";

export function registerClankerCommand(pi: ExtensionAPI) {
    pi.registerCommand("clanker-v2", {
        description: "Open the Clanker Ops v2 Board",
        handler: async (args, ctx) => {
            if (!ctx.hasUI) return;

            let state: UIState = {
                width: process.stdout.columns || 100,
                height: process.stdout.rows || 24,
                tasks: loadTasks(),
                activeIndex: 0,
                activePane: 'center',
                activeTab: 'overview',
                activeBoard: 'Main Ops',
                leftActiveIndex: 0,
                searchQuery: '',
                listScrollOffset: 0,
                inspectorScrollOffset: 0,
                debugEnabled: false
            };

            return new Promise<void>((resolve) => {
                ctx.ui.custom((_tui, _theme, _kb, done) => ({
                    render() {
                        // Update dynamic dimensions
                        state.width = process.stdout.columns || 100;
                        state.height = process.stdout.rows || 24;
                        return renderClankerBoardV2(state);
                    },
                    handleInput(data: string) {
                        if (data === "\x1b" || data === "q") {
                            done(undefined);
                            resolve(); // Exit the TUI
                            return;
                        }

                        if (data === "d") {
                            state.debugEnabled = !state.debugEnabled;
                        }

                        if (data === "\x1b[A" || data === "k") { // up
                            if (state.activePane === 'center') {
                                if (state.activeIndex > 0) {
                                    state.activeIndex--;
                                    if (state.activeIndex < state.listScrollOffset) {
                                        state.listScrollOffset = state.activeIndex;
                                    }
                                }
                            } else if (state.activePane === 'left') {
                                if (state.leftActiveIndex > 0) state.leftActiveIndex--;
                            } else if (state.activePane === 'right') {
                                if (state.inspectorScrollOffset > 0) state.inspectorScrollOffset--;
                            }
                        }

                        if (data === "\x1b[B" || data === "j") { // down
                            if (state.activePane === 'center') {
                                if (state.activeIndex < state.tasks.length - 1) {
                                    state.activeIndex++;
                                    // Assuming approx body height
                                    const visibleItems = state.height - 5;
                                    if (state.activeIndex >= state.listScrollOffset + visibleItems) {
                                        state.listScrollOffset = state.activeIndex - visibleItems + 1;
                                    }
                                }
                            } else if (state.activePane === 'left') {
                                // Currently 4 hardcoded items in left rail
                                if (state.leftActiveIndex < 3) state.leftActiveIndex++;
                            } else if (state.activePane === 'right') {
                                // Assume max scroll is arbitrary for now (we don't compute right pane total height perfectly here)
                                state.inspectorScrollOffset++;
                            }
                        }

                        if (data === "o") {
                            state.activeTab = "overview";
                        }
                        if (data === "p") {
                            state.activeTab = "plan";
                        }
                        if (data === "e") {
                            state.activeTab = "edit";
                        }

                        // Pane Navigation (h/l, left/right, tab)
                        if (data === "\x1b[D" || data === "h") { // left
                            if (state.activePane === 'right') state.activePane = 'center';
                            else if (state.activePane === 'center') state.activePane = 'left';
                        }
                        if (data === "\x1b[C" || data === "l") { // right
                            if (state.activePane === 'left') state.activePane = 'center';
                            else if (state.activePane === 'center') state.activePane = 'right';
                        }
                        if (data === "\t") { // tab cycles left -> center -> right -> left
                            if (state.activePane === 'left') state.activePane = 'center';
                            else if (state.activePane === 'center') state.activePane = 'right';
                            else state.activePane = 'left';
                        }
                        if (data === "\x1b[Z") { // shift+tab cycles backward
                            if (state.activePane === 'left') state.activePane = 'right';
                            else if (state.activePane === 'center') state.activePane = 'left';
                            else state.activePane = 'center';
                        }

                        // Re-render
                        _tui.requestRender();
                    },
                    invalidate() {}
                }));
            });
        }
    });
}
