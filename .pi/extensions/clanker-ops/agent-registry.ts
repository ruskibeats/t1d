import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

export interface AgentDefinition {
	name: string;
	role: string;
	systemPrompt: string;
	verification?: string;
	filePath: string;
}

const AGENTS_DIR = join(process.cwd(), ".pi", "agents");

function parseAgentFile(filePath: string): AgentDefinition | undefined {
	try {
		const content = readFileSync(filePath, "utf-8");
		const basename = filePath.split("/").pop()?.replace(".md", "") ?? "";
		const name = basename.replace(/\.md$/, "");

		// Extract role description from ## Role section (first paragraph, stops at next heading)
		const roleMatch = content.match(/^##\s+Role\s*\n([\s\S]*?)(?=\n## |\n*$)/m);
		const role = roleMatch ? roleMatch[1].trim().split('\n')[0] : name;

		// Extract verification section
		const verificationMatch = content.match(/##\s+Verification[\s\S]*?(?=\n## |\n*$)/);
		const verification = verificationMatch ? verificationMatch[0].replace(/^##\s+Verification\s*/, "").trim() : undefined;

		return {
			name,
			role,
			systemPrompt: content.trim(),
			verification,
			filePath,
		};
	} catch {
		return undefined;
	}
}

function discoverAgents(): Map<string, AgentDefinition> {
	const agents = new Map<string, AgentDefinition>();
	if (!existsSync(AGENTS_DIR)) return agents;

	for (const entry of readdirSync(AGENTS_DIR, { withFileTypes: true })) {
		if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
		const def = parseAgentFile(join(AGENTS_DIR, entry.name));
		if (def) agents.set(def.name, def);
	}
	return agents;
}

let agentCache: Map<string, AgentDefinition> | undefined;

export function resolveAgent(owner: string): AgentDefinition | undefined {
	const cleanName = owner.replace(/^@/, "").trim();
	if (!cleanName) return undefined;

	agentCache ??= discoverAgents();
	return agentCache.get(cleanName);
}

export function invalidateAgentCache(): void {
	agentCache = undefined;
}
