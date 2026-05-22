import { Task, UIState, InspectorViewModel } from "./types.js";
import { truncateToWidth, wrapText, ansi } from "../tui/text.js";

// Maps task status to a colored, unambiguously 1-wide marker.
// NOTE: geometric Unicode symbols (◉ ◎ ✓) are "East Asian Width: Ambiguous"
// and render as 2 columns in many terminals, causing layout crashes.
// Bracket-style ASCII is safe everywhere.
function getStatusIcon(task: Task): string {
    switch (task.status) {
        case 'done':        return ansi.green('[x]');
        case 'in_progress': return ansi.orange('[~]');
        case 'todo':        return ansi.cyan('[ ]');
        default:            return ansi.gray('[?]');
    }
}

// Formats a single task for the center list.
// Format: " │ [x] #13 Set up CI/CD pipeline"
export function formatTaskRow(task: Task, width: number, isSelected: boolean): string {
    const icon    = getStatusIcon(task);
    const idRaw   = `#${task.id}`;
    const idStr   = ansi.gray(idRaw);

    // Prefix is always: " │ " (3) + "[x]" (3) + " " (1) + "#N" (id.len) + " " (1)
    const prefixVisualWidth = 3 + 3 + 1 + idRaw.length + 1; // = 8 + id.length
    const prefixAnsi        = ` │ ${icon} ${idStr} `;

    const availableWidth = Math.max(0, width - prefixVisualWidth - 5);
    const titleStr = truncateToWidth(task.title, availableWidth);

    return prefixAnsi + titleStr;
}


// Generates the content for the right inspector pane
export function getInspectorViewModel(state: UIState, rightPaneWidth: number): InspectorViewModel {
    const activeTask = getFilteredTasks(state)[state.activeIndex];
    if (!activeTask) {
        return { inspectorContent: ["No active task"] };
    }

    const lines: string[] = [];

    if (state.activeTab === 'overview') {
        lines.push(ansi.bold(truncateToWidth(` Task: #${activeTask.id} ${activeTask.title}`, rightPaneWidth)));
        lines.push("");

        let statusDisplay = "To Do";
        if (activeTask.status === 'in_progress') statusDisplay = "In Progress";
        if (activeTask.status === 'done') statusDisplay = "Done";

        lines.push(ansi.gray(" Status:  ") + statusDisplay);
        lines.push(ansi.gray(" Owner:   ") + (activeTask.owner || ansi.gray("none")));
        lines.push(ansi.gray(" Tags:    ") + (activeTask.tags.length > 0 ? activeTask.tags.join(", ") : ansi.gray("none")));
        if (activeTask.planFile) {
            lines.push(ansi.gray(" PlanFile:") + " " + activeTask.planFile);
        }

        lines.push("");
        lines.push(ansi.gray(" Plan:"));
        if (activeTask.description) {
            lines.push(...wrapText(activeTask.description, rightPaneWidth - 1).map(l => " " + l));
        } else {
            lines.push(ansi.gray(" (No plan details)"));
        }
    } else if (state.activeTab === 'plan') {
        lines.push(ansi.bold(` PLAN: Task #${activeTask.id}`));
        lines.push("");
        lines.push(ansi.gray(" Implementation plan details would go here..."));
    } else if (state.activeTab === 'edit' && state.editState) {
        lines.push(ansi.bold(` EDIT: Task #${activeTask.id}`));
        lines.push(...wrapText(activeTask.title, rightPaneWidth));
        lines.push("");

        const es = state.editState;

        const renderField = (index: number, label: string, value: string) => {
            const isActive = es.activeFieldIndex === index;
            const prefix = isActive ? ansi.orange("> ") : "  ";
            return `${prefix}${ansi.gray(label.padEnd(8))} [ ${isActive ? ansi.amber(value) : value} ]`;
        };

        lines.push(renderField(0, "Status:", es.draftStatus));
        lines.push(renderField(1, "Owner:",  es.draftOwner));
        lines.push(renderField(2, "Tags:",   es.draftTags));

        lines.push("");
        lines.push(...wrapText("(UP/DOWN to select field, SPACE to toggle Status/Owner, type to edit Tags, ENTER to save, ESC to cancel)", rightPaneWidth).map(l => ansi.gray(l)));
    }

    return { inspectorContent: lines };
}

export function getFilteredTasks(state: UIState): Task[] {
    let filtered = state.tasks;
    
    if (state.leftActiveIndex === 2) {
        // All Active
        filtered = filtered.filter(t => t.status !== 'done');
    } else if (state.leftActiveIndex === 3) {
        // Completed
        filtered = filtered.filter(t => t.status === 'done');
    } else if (state.leftActiveIndex === 4) {
        // Assigned
        filtered = filtered.filter(t => t.status !== 'done' && (!state.assignedFilterOwner || t.owner === state.assignedFilterOwner));
    } else if (state.leftActiveIndex === 5) {
        // Tags
        filtered = filtered.filter(t => t.tags.includes('ui'));
    }
    
    return filtered;
}
