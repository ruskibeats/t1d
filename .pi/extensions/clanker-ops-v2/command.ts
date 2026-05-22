import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { UIState } from "./state/types.js";
import { loadTasks } from "./state/loadTasks.js";
import { saveTaskMeta } from "./state/saveTasks.js";
import { getFilteredTasks, getSortedTags } from "./state/selectors.js";
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
                        const lowerData = data.toLowerCase();

                        if (state.activeTab === 'edit' && state.editState) {
                            if (data === '\x1b') {
                                state.activeTab = 'overview';
                            } else if (data === '\r' || data === '\n') {
                                // Save
                                const filtered = getFilteredTasks(state);
                                const task = filtered[state.activeIndex];
                                if (!task) return;
                                task.status = state.editState.draftStatus as any;
                                task.owner = state.editState.draftOwner;
                                task.tags = state.editState.draftTags.split(',').map(s => s.trim()).filter(Boolean);
                                saveTaskMeta(task.id, {
                                    status: task.status,
                                    owner: task.owner,
                                    tags: task.tags
                                });
                                state.activeTab = 'overview';
                            } else if (data === '\x1b[A') { // Up
                                state.editState.activeFieldIndex = Math.max(0, state.editState.activeFieldIndex - 1);
                            } else if (data === '\x1b[B') { // Down
                                state.editState.activeFieldIndex = Math.min(2, state.editState.activeFieldIndex + 1);
                            } else if (data === '\x1b[D' || data === '\x1b[C' || data === ' ') { // Left, Right, Space
                                if (state.editState.activeFieldIndex === 0) {
                                    const statuses = ['todo', 'in_progress', 'done'];
                                    const curr = statuses.indexOf(state.editState.draftStatus);
                                    const next = (curr + 1) % statuses.length;
                                    state.editState.draftStatus = statuses[next];
                                } else if (state.editState.activeFieldIndex === 1) {
                                    const owners = ['', '@worker', '@builder', '@scout', '@planner', '@researcher', '@dad_웃', '@tom_웃'];
                                    const curr = owners.indexOf(state.editState.draftOwner);
                                    const next = (curr === -1 ? 0 : curr + 1) % owners.length;
                                    state.editState.draftOwner = owners[next];
                                }
                            } else if (data === '\x7f' || data === '\b') { // Backspace
                                if (state.editState.activeFieldIndex === 2) state.editState.draftTags = state.editState.draftTags.slice(0, -1);
                            } else if (data.length === 1 && !data.startsWith('\x1b')) {
                                // Printable char
                                if (state.editState.activeFieldIndex === 2) state.editState.draftTags += data;
                            }
                            _tui.requestRender();
                            return; // Block normal navigation
                        }

                        if (data === "\x1b" || lowerData === "q") {
                            done(undefined);
                            resolve(); // Exit the TUI
                            return;
                        }

                        if (lowerData === "d") {
                            state.debugEnabled = !state.debugEnabled;
                        }

                        if (data === "\x1b[A" || lowerData === "k") { // up
                            if (state.activePane === 'center') {
                                state.activeTab = "overview"; // Always auto-recover to overview when trying to navigate
                                if (state.activeIndex > 0) {
                                    state.activeIndex--;
                                    if (state.activeIndex < state.listScrollOffset) {
                                        state.listScrollOffset = state.activeIndex;
                                    }
                                }
                            } else if (state.activePane === 'left') {
                                if (state.leftActiveIndex > 0) {
                                    state.leftActiveIndex--;
                                    state.activeIndex = 0;
                                    state.listScrollOffset = 0;
                                }
                            } else if (state.activePane === 'right') {
                                if (state.inspectorScrollOffset > 0) state.inspectorScrollOffset--;
                            }
                        }

                        if (data === "\x1b[B" || lowerData === "j") { // down
                            if (state.activePane === 'center') {
                                state.activeTab = "overview"; // Always auto-recover to overview when trying to navigate
                                const filtered = getFilteredTasks(state);
                                if (state.activeIndex < filtered.length - 1) {
                                    state.activeIndex++;
                                    // Assuming approx body height
                                    const visibleItems = state.height - 5;
                                    if (state.activeIndex >= state.listScrollOffset + visibleItems) {
                                        state.listScrollOffset = state.activeIndex - visibleItems + 1;
                                    }
                                }
                            } else if (state.activePane === 'left') {
                                const maxLeftIndex = 4 + getSortedTags(state.tasks).length;
                                if (state.leftActiveIndex < maxLeftIndex) {
                                    state.leftActiveIndex++;
                                    state.activeIndex = 0;
                                    state.listScrollOffset = 0;
                                }
                            } else if (state.activePane === 'right') {
                                // Assume max scroll is arbitrary for now (we don't compute right pane total height perfectly here)
                                state.inspectorScrollOffset++;
                            }
                        }

                        if (state.activePane === 'left' && state.leftActiveIndex === 4) {
                            if (data === ' ' || data === '\r' || data === '\n') {
                                const owners = ['', '@worker', '@builder', '@scout', '@planner', '@researcher', '@dad_웃', '@tom_웃'];
                                const curr = owners.indexOf(state.assignedFilterOwner || '');
                                const next = (curr === -1 ? 0 : curr + 1) % owners.length;
                                state.assignedFilterOwner = owners[next];
                                state.activeIndex = 0;
                                state.listScrollOffset = 0;
                            }
                        }

                        if (lowerData === "o") {
                            state.activeTab = "overview";
                        }
                        if (lowerData === "p") {
                            state.activeTab = state.activeTab === "plan" ? "overview" : "plan";
                        }
                        if (lowerData === "e") {
                            if (state.activeTab === "edit") {
                                state.activeTab = "overview";
                            } else {
                                state.activeTab = "edit";
                                const filtered = getFilteredTasks(state);
                                const task = filtered[state.activeIndex];
                                if (task) {
                                    state.editState = {
                                        activeFieldIndex: 0,
                                        draftStatus: task.status,
                                        draftOwner: task.owner || '',
                                        draftTags: task.tags.join(', ')
                                    };
                                }
                            }
                        }

                        // Pane Navigation (h/l, left/right, tab)
                        if (data === "\x1b[D" || lowerData === "h") { // left
                            if (state.activePane === 'right') state.activePane = 'center';
                            else if (state.activePane === 'center') state.activePane = 'left';
                        }
                        if (data === "\x1b[C" || lowerData === "l") { // right
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
