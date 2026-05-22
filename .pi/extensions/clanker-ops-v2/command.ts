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
                width: ctx.ui.columns(),
                height: ctx.ui.rows(),
                tasks: loadTasks(),
                activeIndex: 0,
                activePane: 'center',
                activeTab: 'overview',
                activeBoard: 'Main Ops',
                searchQuery: '',
                listScrollOffset: 0,
                inspectorScrollOffset: 0,
                debugEnabled: false
            };

            return new Promise<void>((resolve) => {
                ctx.ui.custom({
                    render() {
                        // Update dynamic dimensions
                        state.width = ctx.ui.columns();
                        state.height = ctx.ui.rows();
                        return renderClankerBoardV2(state);
                    },
                    handleKey(key: any) {
                        if (key.name === "escape" || key.name === "q") {
                            resolve(); // Exit the TUI
                            return true;
                        }

                        if (key.name === "d") {
                            state.debugEnabled = !state.debugEnabled;
                        }

                        if (key.name === "up") {
                            if (state.activeIndex > 0) {
                                state.activeIndex--;
                                if (state.activeIndex < state.listScrollOffset) {
                                    state.listScrollOffset = state.activeIndex;
                                }
                            }
                        }

                        if (key.name === "down") {
                            if (state.activeIndex < state.tasks.length - 1) {
                                state.activeIndex++;
                                // Assuming approx body height
                                const visibleItems = state.height - 5;
                                if (state.activeIndex >= state.listScrollOffset + visibleItems) {
                                    state.listScrollOffset = state.activeIndex - visibleItems + 1;
                                }
                            }
                        }

                        if (key.name === "o") {
                            state.activeTab = "overview";
                        }
                        if (key.name === "p") {
                            state.activeTab = "plan";
                        }
                        if (key.name === "e") {
                            state.activeTab = "edit";
                        }

                        // Re-render
                        ctx.ui.refresh();
                        return true;
                    }
                });
            });
        }
    });
}
