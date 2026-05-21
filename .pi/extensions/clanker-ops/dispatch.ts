import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { getState } from "./state/store.js";
import { resolveAgent } from "./agent-registry.js";

export interface DispatchPayload {
	taskId: number;
	runId: string;
	agent: string;
	agentFilePath: string;
	task: string;
	planPath: string;
	outputPath: string;
	controlIntercomTarget: string;
}

function generateRunId(): string {
	return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

function extractPlanSections(content: string): {
	steps: string[];
	verification: string[];
	outcome: string;
} {
	const lines = content.split(/\r?\n/);
	const sections: Record<string, string[]> = {};
	let currentSection = "";

	for (const line of lines) {
		const headerMatch = line.match(/^#{2,4}\s+(.+)/);
		if (headerMatch) {
			currentSection = headerMatch[1].toLowerCase().replace(/\s+/g, "_");
			sections[currentSection] = [];
		} else if (currentSection) {
			sections[currentSection].push(line);
		}
	}

	const steps = sections["steps"]?.filter((l) => l.trim()) ?? [];
	const verification = sections["verification"]?.filter((l) => l.trim()) ?? [];
	const outcome = sections["intended_outcome"]?.filter((l) => l.trim()).join(" ") ?? "";

	return { steps, verification, outcome };
}

export function assembleDispatch(taskId: number): DispatchPayload | null {
	const state = getState();
	const task = state.tasks.find((t) => t.id === taskId);
	if (!task) {
		console.error(`Dispatch failed: task #${taskId} not found`);
		return null;
	}

	const owner = task.assigned ?? task.owner;
	if (!owner) {
		console.error(`Dispatch failed: task #${taskId} has no assigned owner`);
		return null;
	}

	const agent = resolveAgent(owner);
	if (!agent) {
		console.error(`Dispatch failed: unknown agent owner "${owner}". No .pi/agents/${owner.replace(/^@/, "")}.md found.`);
		return null;
	}

	const planPath = task.planFile
		? join(process.cwd(), ".pi", "todo-plans", task.planFile)
		: join(process.cwd(), ".pi", "todo-plans", `#${taskId}_plan.md`);

	if (!existsSync(planPath)) {
		console.error(`Dispatch failed: plan file not found at ${planPath}`);
		return null;
	}

	const planContent = readFileSync(planPath, "utf-8");
	const { steps, verification, outcome } = extractPlanSections(planContent);

	const runId = generateRunId();
	const outputPath = join(process.cwd(), ".pi", "todo-plans", `dispatch-${taskId}-${runId}.md`);

	// Build the subagent task instruction
	const taskLines: string[] = [
		`Execute Clanker Ops task #${taskId} per the attached plan.`,
		`"""`,
		`Plan file: ${planPath}`,
		`Agent role: ${agent.role}`,
		`",`,
	];

	if (outcome) {
		taskLines.push(`Intended outcome: ${outcome}`);
	}

	if (steps.length > 0) {
		taskLines.push(`Key steps:`);
		for (const step of steps.slice(0, 8)) {
			taskLines.push(`  - ${step.trim()}`);
		}
		if (steps.length > 8) taskLines.push(`  ... (${steps.length - 8} more steps in plan file)`);
	}

	if (verification.length > 0) {
		taskLines.push(`Verification:`);
		for (const v of verification.slice(0, 4)) {
			taskLines.push(`  - ${v.trim()}`);
		}
	}

	taskLines.push(`"""`);
	taskLines.push(`After completing, write a closeout summary to the plan file under ### Agent Log and update task status.`);

	return {
		taskId,
		runId,
		agent: agent.name,
		agentFilePath: agent.filePath,
		task: taskLines.join("\n"),
		planPath,
		outputPath,
		controlIntercomTarget: `clanker-controller-${process.pid}`,
	};
}
