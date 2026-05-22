import fs from "fs";
import path from "path";
import { Task } from "./types.js";

export function saveTaskMeta(taskId: string, updates: Partial<Task>) {
    try {
        const dataPath = path.join(process.cwd(), ".pi", "todo-state.json");
        if (fs.existsSync(dataPath)) {
            const raw = fs.readFileSync(dataPath, "utf-8");
            const parsed = JSON.parse(raw);
            if (parsed.items && Array.isArray(parsed.items)) {
                let updated = false;
                for (const item of parsed.items) {
                    if (String(item.id) === taskId) {
                        if (updates.status) {
                            if (updates.status === 'done') item.status = 'completed';
                            else if (updates.status === 'in_progress') item.status = 'in-progress';
                            else if (updates.status === 'todo') item.status = 'pending';
                        }
                        if (updates.owner !== undefined) {
                            item.assigned = updates.owner;
                        }
                        if (updates.tags !== undefined) {
                            item.tags = updates.tags;
                        }
                        updated = true;
                        break;
                    }
                }
                
                if (updated) {
                    fs.writeFileSync(dataPath, JSON.stringify(parsed, null, 2), "utf-8");
                }
            }
        }
    } catch (e) {
        console.error("Failed to save tasks:", e);
    }
}
