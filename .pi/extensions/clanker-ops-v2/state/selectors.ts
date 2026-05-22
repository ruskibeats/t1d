import { Task, UIState, InspectorViewModel } from "./types.js";
import { truncateToWidth, wrapText } from "../tui/text.js";

// Formats a single task for the center list
export function formatTaskRow(task: Task, width: number, isSelected: boolean): string {
    const statusBox = task.status === 'done' ? '[x]' : '[ ]';
    const idStr = `#${task.id}`;
    
    // 1. Status and ID are never truncated
    const prefix = `${statusBox} ${idStr} `;
    
    // 2. Title gets heavily truncated if necessary
    const availableWidth = width - prefix.length;
    const titleStr = truncateToWidth(task.title, Math.max(0, availableWidth));
    
    return prefix + titleStr;
}

// Generates the content for the right inspector pane
export function getInspectorViewModel(state: UIState, rightPaneWidth: number): InspectorViewModel {
    const activeTask = state.tasks[state.activeIndex];
    if (!activeTask) {
        return { inspectorContent: ["No active task"] };
    }

    const lines: string[] = [];
    
    if (state.activeTab === 'overview') {
        lines.push(`TASK #${activeTask.id}`);
        lines.push(...wrapText(activeTask.title, rightPaneWidth));
        lines.push("");
        
        let statusDisplay = "To Do";
        if (activeTask.status === 'in_progress') statusDisplay = "In Progress";
        if (activeTask.status === 'done') statusDisplay = "Done";
        lines.push(`Status:   ${statusDisplay}`);
        lines.push(`Owner:    ${activeTask.owner || 'Unassigned'}`);
        lines.push(`Tags:     ${activeTask.tags.length > 0 ? activeTask.tags.join(', ') : 'None'}`);
        if (activeTask.planFile) {
            lines.push(`PlanFile: ${activeTask.planFile}`);
        }
        
        lines.push("");
        lines.push("Description & Plan:");
        if (activeTask.description) {
            lines.push(...wrapText(activeTask.description, rightPaneWidth));
        } else {
            lines.push("No description provided.");
        }
    } else if (state.activeTab === 'plan') {
        lines.push(`PLAN: TASK #${activeTask.id}`);
        lines.push("Implementation plan details would go here...");
        // In the future, this would load planText from the task model
    } else if (state.activeTab === 'edit') {
        lines.push(`EDIT: TASK #${activeTask.id}`);
        lines.push("(Editing interface placeholder)");
    }

    return { inspectorContent: lines };
}
