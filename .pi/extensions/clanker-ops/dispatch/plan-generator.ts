/**
 * Plan Generator — Auto-generates plan files for dispatch.
 *
 * When `/clanker dispatch #N to @agent` is called and no plan file exists,
 * this module reads the task description + agent definition and generates
 * a stub plan with Intended Outcome, Step-by-Step, Verification, and Audit.
 */

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import type { Task } from "../tool/types.js";
import { resolveAgent } from "../agent-registry.js";

// ---------------------------------------------------------------------------
// Plan file path
// ---------------------------------------------------------------------------

export function planFilePath(taskId: number): string {
	return join(process.cwd(), ".pi", "todo-plans", `#${taskId}_plan.md`);
}

export function planExists(taskId: number): boolean {
	return existsSync(planFilePath(taskId));
}

// ---------------------------------------------------------------------------
// Generation
// ---------------------------------------------------------------------------

export interface GeneratePlanInput {
	task: Task;
	agentName: string;
}

export interface GeneratePlanResult {
	generated: boolean;
	path?: string;
	reason?: string;
}

/**
 * Generates a plan file for a task if one doesn't exist.
 * Uses the task description + agent definition to produce a stub.
 */
export function generatePlan(input: GeneratePlanResult): GeneratePlanResult {
	if (planExists(input.task.id)) {
		return { generated: false, reason: "Plan file already exists" };
	}

	if (!input.task.item && !input.task.description) {
		return { generated: false, reason: "Task has no description or title to generate a plan from" };
	}

	const agent = resolveAgent(input.agentName);
	if (!agent) {
		return { generated: false, reason: `Agent "${input.agentName}" not found in registry` };
	}

	const planPath = planFilePath(input.task.id);
	const content = buildPlanContent(input.task, agent);
	
	try {
		mkdirSync(dirname(planPath), { recursive: true });
		writeFileSync(planPath, content, "utf-8");
		return { generated: true, path: planPath };
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		return { generated: false, reason: `Failed to write plan: ${message}` };
	}
}

// ---------------------------------------------------------------------------
// Plan content template
// ---------------------------------------------------------------------------

function buildPlanContent(task: Task, agent: { name: string; role: string }): string {
	const now = new Date().toISOString().slice(0, 16).replace("T", " ");
	const title = task.item;
	const description = task.description || "";
	const agentRole = agent.role;

	return [
		`# ${title}`,
		"",
		`Auto-generated plan for dispatch to @${agent.name}`,
		`Generated: ${now}`,
		"",
		"## Intended Outcome",
		"",
		description || `${title} — completed and verified.`,
		"",
		"## Step-by-Step",
		"",
		`Using the ${agentRole} role:`,
		"1. Explore the codebase and understand the current state",
		"2. Implement changes per the task description",
		"3. Test the implementation",
		"4. Document any findings",
		"",
		"## Verification",
		"",
		"- [ ] The implementation satisfies the task description",
		"- [ ] Tests pass",
		"- [ ] Changes follow established code patterns",
		"- [ ] Documentation is updated if needed",
		"",
		"## Dependencies",
		"",
		...(task.blockedBy?.length
			? task.blockedBy.map((id) => `- #${id}`)
			: ["- None"]),
		"",
		"## Audit",
		"",
		"| Time | Event |",
		"|------|-------|",
		`| ${now} | Plan auto-generated for dispatch to @${agent.name} |`,
		"",
		"---",
		"",
		"### Agent Log",
		"",
	].join("\n");
}