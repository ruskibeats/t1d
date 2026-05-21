/**
 * Process Spawner — Handles subprocess creation for background dispatch.
 *
 * Extracted from background-spawner.ts. Encapsulates child_process.spawn
 * invocation with proper error handling, PID capture, and fallback
 * command generation.
 */

import { spawn } from "node:child_process";
import type { DispatchPayload } from "../dispatch.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SpawnResult {
	autoSpawned: boolean;
	pid?: number;
	runId: string;
	error?: string;
	fallbackCommand?: string;
}

export interface SpawnDeps {
	/** Path to jiti CLI entry point */
	jitiPath: string;
	/** Path to pi-subagents runner script */
	runnerPath: string;
	/** Path to config file on disk */
	configPath: string;
	/** Current working directory */
	cwd: string;
}

// ---------------------------------------------------------------------------
// Fallback command generation
// ---------------------------------------------------------------------------

export function buildFallbackCommand(payload: DispatchPayload): string {
	return `subagent single --agent ${payload.agent} --async true --output ${payload.outputPath} --task "${payload.task.replace(/"/g, '\\"')}"`;
}

// ---------------------------------------------------------------------------
// Core spawn logic
// ---------------------------------------------------------------------------

export function spawnBackgroundProcess(deps: SpawnDeps): SpawnResult {
	const proc = spawn(process.execPath, [deps.jitiPath, deps.runnerPath, deps.configPath], {
		cwd: deps.cwd,
		detached: true,
		stdio: "ignore",
		windowsHide: true,
	});

	proc.on("error", (error) => {
		console.error(`[clanker-ops] spawn error: ${error.message}`);
	});

	if (typeof proc.pid !== "number") {
		return {
			autoSpawned: false,
			runId: deps.configPath,
			error: "spawn did not produce a PID",
		};
	}

	proc.unref();

	return {
		autoSpawned: true,
		pid: proc.pid,
		runId: deps.configPath,
	};
}

// ---------------------------------------------------------------------------
// Full dispatch execution (composes resolver + config + spawn)
// ---------------------------------------------------------------------------

import { resolveAllPaths } from "./resolver.js";
import { buildRunnerConfig, writeConfigToDisk } from "./config-builder.js";

export function executeBackgroundDispatch(payload: DispatchPayload): SpawnResult {
	// Step 1: Resolve paths
	const paths = resolveAllPaths();
	if (!paths.resolved) {
		return {
			autoSpawned: false,
			runId: payload.runId,
			error: paths.error ?? "path resolution failed",
			fallbackCommand: buildFallbackCommand(payload),
		};
	}

	// Step 2: Build config
	const config = buildRunnerConfig(payload);

	// Step 3: Write config to disk
	const writeResult = writeConfigToDisk(config);
	if (!writeResult.success) {
		return {
			autoSpawned: false,
			runId: payload.runId,
			error: writeResult.error ?? "config write failed",
			fallbackCommand: buildFallbackCommand(payload),
		};
	}

	// Step 4: Spawn
	return spawnBackgroundProcess({
		jitiPath: paths.jiti,
		runnerPath: paths.runner,
		configPath: writeResult.path!,
		cwd: process.cwd(),
	});
}