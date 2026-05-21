---
name: "deepen-background-spawner"
description: "Decompose a monolithic background subprocess spawner into three focused modules: Resolver (path resolution), Config Builder (construct/write config), and Process Spawner (subprocess lifecycle). Use when a spawner module mixes node_modules traversal, config construction, and child_process.spawn in one file."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

- A background spawner module (300+ lines) mixes path resolution, config construction, and subprocess spawning
- You need to unit-test path resolution or config building without actually spawning a subprocess
- You need multiple dispatch strategies (auto-spawn vs. fallback command) and the current module can't cleanly support both
- The spawner module has hard-to-test `try/catch` blocks that mix I/O errors with resolution logic
- You're extending a CLI tool or Pi extension that spawns detached subprocesses (e.g., pi-subagents background runners)

## Procedure

### 1. Identify the mixed concerns in the spawner module

A monolithic background spawner typically mixes these concerns:

| Concern | What it does | Why extract it |
|---------|-------------|----------------|
| **Path Resolution** | Traverses node_modules to find the jiti CLI binary and runner script | Testable without spawning; reusable across different spawn contexts |
| **Config Construction** | Builds the JSON config object the runner expects and writes it to disk | Pure data transformation; testable in isolation |
| **Process Spawning** | Calls `child_process.spawn`, captures PID, handles errors | I/O-bound; needs to be mocked in tests; varies by platform |

### 2. Create the resolver module (`dispatch/resolver.ts`)

Encapsulates all filesystem traversal for finding the jiti CLI entry point and runner script.

```typescript
// dispatch/resolver.ts — Path resolution only
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { createRequire } from "node:module";

export interface ResolvedPaths {
  jiti: string;
  runner: string;
  resolved: boolean;
  error?: string;
}

function resolveJitiCliFromPackageJson(packageJsonPath: string): string | undefined {
  if (!existsSync(packageJsonPath)) return undefined;
  const packageRoot = dirname(packageJsonPath);
  const pkg = JSON.parse(readFileSync(packageJsonPath, "utf-8")) as {
    bin?: string | Record<string, string>;
  };
  const binField = pkg.bin;
  const binPath = typeof binField === "string"
    ? binField
    : binField?.jiti ?? Object.values(binField ?? {})[0];
  const candidates = [binPath, "lib/jiti-cli.mjs"].filter(Boolean);
  for (const candidate of candidates) {
    const cliPath = resolve(packageRoot, candidate);
    if (existsSync(cliPath)) return cliPath;
  }
  return undefined;
}

export function resolveAllPaths(): ResolvedPaths {
  // Multiple candidate strategies: require.resolve, createRequire, hardcoded fallback
  const jiti = resolveJitiCliPath(); // Try require.resolve first, then createRequire
  const runner = resolveRunnerScript(); // Try require.resolve, then hardcoded fallback
  // ... return structured result with error messages
}
```

**Key patterns**:
- **Fallback chain**: Try `require.resolve` → `createRequire` → hardcoded path. Each candidate wrapped in `try/catch`.
- **`package.json` bin field parsing**: Extract the binary path from the `bin` field (handles both string and Record<string, string> forms).
- **Structured return**: Return a `ResolvedPaths` object with `resolved: boolean` and `error?: string` rather than throwing or returning `undefined`.

### 3. Create the config builder module (`dispatch/config-builder.ts`)

Encapsulates mapping dispatch parameters to runner config and writing to disk.

```typescript
// dispatch/config-builder.ts — Config construction + disk write
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

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
  artifactsDir: string;
  artifactConfig: { enabled: boolean };
}

export function buildRunnerConfig(payload: DispatchPayload, configDir: string): RunnerConfig {
  return {
    id: payload.runId,
    steps: [{
      agent: payload.agent,
      task: payload.task,
      cwd: payload.cwd,
      skills: payload.skills ?? [],
      maxSubagentDepth: 1,
    }],
    resultPath: join(configDir, "result.json"),
    cwd: payload.cwd,
    artifactsDir: join(configDir, "artifacts"),
    artifactConfig: { enabled: true },
  };
}

export function writeConfigToDisk(configDir: string, config: RunnerConfig): string {
  mkdirSync(configDir, { recursive: true });
  const configPath = join(configDir, "config.json");
  writeFileSync(configPath, JSON.stringify(config, null, 2), "utf-8");
  return configPath;
}

export function validateCwd(cwd: string): { valid: true } | { valid: false; error: string } {
  if (!cwd) return { valid: false, error: "cwd is required" };
  if (!existsSync(cwd)) return { valid: false, error: `cwd does not exist: ${cwd}` };
  // existsSync returns boolean, not Dirent — don't try to call .isDirectory()
  return { valid: true };
}
```

**Key patterns**:
- **Pure config construction**: `buildRunnerConfig` is a pure function — testable without I/O.
- **Structured validation**: `validateCwd` returns a discriminated union `{valid: true} | {valid: false; error: string}` instead of throwing.
- **Disk write is a separate function**: `writeConfigToDisk` is I/O-bound and can be mocked in tests.
- **`existsSync` returns boolean**: It returns `boolean`, not a `Dirent` object — avoid calling `.isDirectory()` on it.

### 4. Create the process spawner module (`dispatch/process-spawner.ts`)

Encapsulates subprocess creation, PID capture, error handling, and fallback command generation.

```typescript
// dispatch/process-spawner.ts — Process lifecycle
import { spawn } from "node:child_process";

export interface SpawnResult {
  autoSpawned: boolean;
  pid?: number;
  runId: string;
  error?: string;
  fallbackCommand?: string;
}

export interface SpawnDeps {
  jitiPath: string;
  runnerPath: string;
  configPath: string;
  cwd: string;
  runId: string;
}

export function spawnBackgroundProcess(deps: SpawnDeps): SpawnResult {
  const { jitiPath, runnerPath, configPath, cwd, runId } = deps;
  try {
    const child = spawn(
      "node",
      [jitiPath, runnerPath, "--config", configPath],
      {
        cwd,
        stdio: ["ignore", "pipe", "pipe"],
        detached: true,
      },
    );
    child.unref();
    return { autoSpawned: true, pid: child.pid ?? undefined, runId };
  } catch (err) {
    const fallback = `node ${jitiPath} ${runnerPath} --config ${configPath}`;
    return {
      autoSpawned: false,
      runId,
      error: String(err),
      fallbackCommand: `cd ${cwd} && ${fallback}`,
    };
  }
}
```

**Key patterns**:
- **`child.unref()`**: Prevents the subprocess from keeping the parent process alive.
- **Detached spawn**: `detached: true` so the child survives parent exit.
- **Fallback command**: When spawn fails (e.g., jiti not found), generate a human-executable fallback command string.
- **PID capture**: `child.pid ?? undefined` for safe null handling.

### 5. Refactor the original module into a thin facade

```typescript
// background-spawner.ts — Thin facade
export { spawnBackgroundProcess } from "./dispatch/process-spawner.js";
export { resolveJitiCliPath, resolveRunnerScript, resolveAllPaths } from "./dispatch/resolver.js";
export { buildRunnerConfig, writeConfigToDisk, validateCwd } from "./dispatch/config-builder.js";

// Compose for the most common use case
export async function executeBackgroundDispatch(payload: DispatchPayload): Promise<SpawnResult> {
  const paths = resolveAllPaths();
  if (!paths.resolved) {
    return { autoSpawned: false, runId: payload.runId, error: paths.error };
  }
  const cwdValidation = validateCwd(payload.cwd);
  if (!cwdValidation.valid) {
    return { autoSpawned: false, runId: payload.runId, error: cwdValidation.error };
  }
  const configDir = join(payload.cwd, ".pi", ".dispatch", payload.runId);
  const config = buildRunnerConfig(payload, configDir);
  const configPath = writeConfigToDisk(configDir, config);
  return spawnBackgroundProcess({
    jitiPath: paths.jiti,
    runnerPath: paths.runner,
    configPath,
    cwd: payload.cwd,
    runId: payload.runId,
  });
}
```

### 6. Verify compilation and backward compatibility

```bash
# Ensure all imports resolve
npx tsc --noEmit

# Check that existing callers still work (they import from the facade, not internals)
grep -r "background-spawner" .pi/extensions/ --include="*.ts"

# Verify no circular imports between new modules
npx madge --circular --extensions ts .pi/extensions/<name>/dispatch/
```

## Pitfalls

- **`existsSync` returns boolean**: It returns `boolean`, not a `Dirent` object. Do NOT call `.isDirectory()` on its result — that's a `statSync` pattern. The bug manifests as "existsSync(...).isDirectory is not a function".
- **`require.resolve` vs `createRequire`**: `require.resolve` looks up from the current module's `node_modules`. `createRequire(path)` creates a require function scoped to a specific path. Use `createRequire` when the target package might be in a different `node_modules` tree.
- **Fallback chain must be lenient**: Each candidate in the resolution chain must be wrapped in its own `try/catch` or `if (existsSync(...))`. A throw from one candidate must not abort subsequent candidates.
- **Disk writes in config builder should be explicit**: Keep `writeConfigToDisk` as a separate function from `buildRunnerConfig` so tests can test the pure function without filesystem side effects.
- **Unref detached children**: Always call `child.unref()` on detached spawns. Without it, the parent process may not exit cleanly.
- **Re-export public API from facade**: After extraction, ensure the original module re-exports all types and functions that external importers use. Check for `export type { ... }` as well as `export { ... }`.
- **CWD validation edge cases**: An empty string, a relative path, and a non-existent path should all produce distinct error messages. Test these explicitly.

## Verification

- [ ] `npx tsc --noEmit` passes with zero errors
- [ ] Original module compiles as a thin facade importing from three new modules
- [ ] `dispatch/resolver.ts` is testable without spawning (pure path resolution)
- [ ] `dispatch/config-builder.ts` has a pure `buildRunnerConfig` function separable from `writeConfigToDisk`
- [ ] `dispatch/process-spawner.ts` properly `unref()`s detached children
- [ ] No circular imports between dispatch modules: `npx madge --circular --extensions ts .pi/extensions/<name>/dispatch/`
- [ ] Fallback command is generated when auto-spawn fails
- [ ] Resolver handles all resolution strategies (require.resolve, createRequire, hardcoded fallback)