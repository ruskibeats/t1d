import fs from "fs";
import path from "path";
import { Task } from "./types.js";

export function loadTasks(): Task[] {
    try {
        const dataPath = path.join(process.cwd(), ".pi", "extensions", "clanker-ops-v2", "data.json");
        if (fs.existsSync(dataPath)) {
            const raw = fs.readFileSync(dataPath, "utf-8");
            return JSON.parse(raw) as Task[];
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
