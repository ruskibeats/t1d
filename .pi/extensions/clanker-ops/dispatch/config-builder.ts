/**
 * Config Builder — Builds the pi-subagents runner config JSON.
 *
 * Extracted from background-spawner.ts. Pure function that maps
 * a DispatchPayload into the config object expected by the
 * pi-subagents background runner. Testable without spawning.
 */

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import type { DispatchPayload } from "../dispatch.js";

// ---------------------------------------------------------------------------
// Pi-subagents runner config shape
// ---------------------------------------------------------------------------

export interface RunnerConfig {
	id: string;
	steps: Array<{
		agent: string;
		task: string;
		cwd: string;
		skills: string[];
		maxSubagentDepth: number;
	}>;
	resultPath: string;
	cwd: string;
	placeholder: string;
	artifactsDir: string;
	artifactConfig: { enabled: boolean };
	share: boolean;
	asyncDir: string;
	sessionId: string;
	piPackageRoot: string;
	piArgv1: string;
	controlConfig: {
		enabled: boolean;
		needsAttentionAfterMs: number;
		activeNoticeAfterMs: number;
		failedToolAttemptsBeforeAttention: number;
		notifyOn: string[];
		notifyChannels: string[];
	};
	controlIntercomTarget: string;
	childIntercomTargets: string[];
	resultMode: string;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

export const DEFAULT_CONTROL_CONFIG = {
	enabled: true,
	needsAttentionAfterMs: 60_000,
	activeNoticeAfterMs: 240_000,
	failedToolAttemptsBeforeAttention: 3,
	notifyOn: ["active_long_running", "needs_attention"] as const,
	notifyChannels: ["event", "intercom"] as const,
};

// ---------------------------------------------------------------------------
// Config builder
// ---------------------------------------------------------------------------

export function buildRunnerConfig(payload: DispatchPayload): RunnerConfig {
	const tempDir = "/tmp/clanker-dispatch";

	return {
		id: payload.runId,
		steps: [
			{
				agent: payload.agent,
				task: payload.task,
				cwd: process.cwd(),
				skills: [],
				maxSubagentDepth: 2,
			},
		],
		resultPath: join(tempDir, `result-${payload.runId}.json`),
		cwd: process.cwd(),
		placeholder: "{previous}",
		artifactsDir: tempDir,
		artifactConfig: { enabled: true },
		share: false,
		asyncDir: join(tempDir, payload.runId),
		sessionId: `clanker-${payload.runId}`,
		piPackageRoot: dirname(require.resolve("pi-subagents/package.json")),
		piArgv1: process.argv[1] ?? "",
		controlConfig: { ...DEFAULT_CONTROL_CONFIG },
		controlIntercomTarget: payload.controlIntercomTarget,
		childIntercomTargets: [`subagent-worker-${payload.runId}-1`],
		resultMode: "single",
	};
}

// ---------------------------------------------------------------------------
// Config serialization
// ---------------------------------------------------------------------------

export interface WriteConfigResult {
	success: boolean;
	path?: string;
	error?: string;
}

export function writeConfigToDisk(config: RunnerConfig): WriteConfigResult {
	const tempDir = "/tmp/clanker-dispatch";
	const cfgPath = join(tempDir, `config-${config.id}.json`);

	try {
		mkdirSync(tempDir, { recursive: true });
		writeFileSync(cfgPath, JSON.stringify(config, null, 2));
		return { success: true, path: cfgPath };
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		return { success: false, error: `Failed to write config: ${message}` };
	}
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

export interface ValidateCwdResult {
	valid: boolean;
	error?: string;
}

export function validateCwd(): ValidateCwdResult {
	try {
		if (!existsSync(process.cwd())) {
			return { valid: false, error: `cwd does not exist: ${process.cwd()}` };
		}
		return { valid: true };
	} catch {
		return { valid: false, error: `cwd check failed: ${process.cwd()}` };
	}
}