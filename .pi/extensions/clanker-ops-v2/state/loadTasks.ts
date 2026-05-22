import fs from "fs";
import path from "path";
import { Task } from "./types.js";

export function loadTasks(): Task[] {
    try {
        const dataPath = path.join(process.cwd(), ".pi", "todo-state.json");
        if (fs.existsSync(dataPath)) {
            const raw = fs.readFileSync(dataPath, "utf-8");
            const parsed = JSON.parse(raw);
            if (parsed.items && Array.isArray(parsed.items)) {
                return parsed.items.map((item: any) => {
                    let mappedStatus: 'todo' | 'in_progress' | 'done' = 'todo';
                    if (item.status === 'completed') mappedStatus = 'done';
                    else if (item.status === 'in-progress' || item.status === 'in_progress' || item.status === 'pending') mappedStatus = 'in_progress';
                    // map deferred or others to todo

                    return {
                        id: String(item.id),
                        title: item.item || "Untitled",
                        status: mappedStatus,
                        tags: item.tags || [],
                        owner: item.assigned || undefined,
                        description: item.description || ""
                    };
                });
            }
        }
    } catch (e) {
        console.error("Failed to load tasks:", e);
    }
    
    // Fallback v1 data if file doesn't exist
    return [
        {
            id: "104",
            title: "Refactor auth module",
            status: "todo",
            tags: ["backend"],
            owner: "@russell",
            description: "Move JWT logic to a separate middleware..."
        },
        {
            id: "105",
            title: "Implement 3-pane TUI layout",
            status: "todo",
            tags: ["ui", "frontend"],
            owner: "@russell",
            description: "We need to completely rewrite the rendering engine to respect strict width budgets."
        },
        {
            id: "106",
            title: "Fix padding overflow bug",
            status: "done",
            tags: ["bug"],
            owner: "@russell",
            description: "Padding calculation doesn't account for ANSI."
        },
        {
            id: "107",
            title: "Update README docs",
            status: "todo",
            tags: ["docs"],
            owner: "@russell",
            description: "Document the new v2 architecture."
        }
    ];
}
