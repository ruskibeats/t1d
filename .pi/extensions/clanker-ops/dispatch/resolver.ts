/**
 * Resolver — Path resolution for jiti CLI and pi-subagents runner.
 *
 * Extracted from background-spawner.ts to isolate the node_modules
 * traversal logic for path resolution. Testable without spawning.
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { createRequire } from "node:module";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ResolvedPaths {
	/** Absolute path to jiti CLI entry point */
	jiti: string;
	/** Absolute path to pi-subagents background runner script */
	runner: string;
	/** Whether both paths resolved successfully */
	resolved: boolean;
	/** Error message if resolution failed */
	error?: string;
}

// ---------------------------------------------------------------------------
// Jiti CLI path resolution
// ---------------------------------------------------------------------------

function resolveJitiCliFromPackageJson(packageJsonPath: string): string | undefined {
	if (!existsSync(packageJsonPath)) return undefined;

	const packageRoot = dirname(packageJsonPath);
	const pkg = JSON.parse(readFileSync(packageJsonPath, "utf-8")) as {
		bin?: string | Record<string, string>;
	};
	const binField = pkg.bin;
	const binPath =
		typeof binField === "string"
			? binField
			: binField?.jiti ?? Object.values(binField ?? {})[0];

	const candidates = [binPath, "lib/jiti-cli.mjs"].filter((c): c is string => Boolean(c));
	for (const candidate of candidates) {
		const cliPath = resolve(packageRoot, candidate);
		if (existsSync(cliPath)) return cliPath;
	}
	return undefined;
}

export function resolveJitiCliPath(): string | undefined {
	const candidates: Array<() => string | undefined> = [
		() => {
			try {
				return require.resolve("jiti/package.json");
			} catch {
				return undefined;
			}
		},
		() => {
			try {
				const subagentsRoot = dirname(require.resolve("pi-subagents/package.json"));
				return resolve(subagentsRoot, "node_modules", "jiti", "package.json");
			} catch {
				return undefined;
			}
		},
		() => {
			try {
				const req = createRequire(
					"/root/.pi/agent/npm/node_modules/pi-subagents/package.json",
				);
				return req.resolve("jiti/package.json");
			} catch {
				return undefined;
			}
		},
	];

	for (const candidate of candidates) {
		try {
			const pkgJson = candidate();
			if (!pkgJson) continue;
			const cli = resolveJitiCliFromPackageJson(pkgJson);
			if (cli) return cli;
		} catch {
			// Candidate unavailable — skip
		}
	}
	return undefined;
}

// ---------------------------------------------------------------------------
// Runner script resolution
// ---------------------------------------------------------------------------

export function resolveRunnerScript(): string | undefined {
	const candidates = [
		() => require.resolve("pi-subagents/src/runs/background/subagent-runner.ts"),
		"/root/.pi/agent/npm/node_modules/pi-subagents/src/runs/background/subagent-runner.ts",
	] as const;

	for (const candidate of candidates) {
		try {
			const p = typeof candidate === "function" ? candidate() : candidate;
			if (existsSync(p)) return p;
		} catch {
			// Continue
		}
	}
	return undefined;
}

// ---------------------------------------------------------------------------
// Combined resolver
// ---------------------------------------------------------------------------

export function resolveAllPaths(): ResolvedPaths {
	const jiti = resolveJitiCliPath();
	const runner = resolveRunnerScript();

	if (!jiti) {
		return {
			jiti: "",
			runner: runner ?? "",
			resolved: false,
			error: "jiti CLI not found; cannot spawn background runner",
		};
	}

	if (!runner) {
		return {
			jiti,
			runner: "",
			resolved: false,
			error: "pi-subagents runner script not found",
		};
	}

	return { jiti, runner, resolved: true };
}