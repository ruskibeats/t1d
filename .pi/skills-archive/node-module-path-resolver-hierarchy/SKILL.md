---
name: "node-module-path-resolver-hierarchy"
description: "Resolve Node.js module paths with a hierarchical fallback strategy. Tries require.resolve, then walks from sibling module dirs, then hardcoded fallbacks. Use when a project tool or runtime script must be located from within a Node.js extension or CLI tool."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Node Module Path Resolver with Fallback Hierarchy

Resolve Node.js module paths (tool CLIs, package.json, runtime scripts) using a multi-strategy fallback hierarchy. The pattern: prefer `require.resolve` → fall back to walking from sibling module directories → fall back to hardcoded absolute paths.

## When to Use

- Your extension or CLI tool needs to locate a peer dependency's entry point (e.g., jiti CLI, pi-subagents runner).
- The install layout is unpredictable — the target could be in the project's `node_modules`, a parent workspace, or the user's global install.
- You want a self-healing resolver that degrades gracefully with a clear error message and fallback command.

## Architecture

```
resolveSomething()
├── Strategy 1: require.resolve("some-package/package.json")
│   → Read bin field, resolve entry point
├── Strategy 2: Walk from pi-subagents/package.json dir
│   → resolve(root, "node_modules", "some-package", "package.json")
├── Strategy 3: Hardcoded absolute fallback
│   → /root/.pi/agent/npm/node_modules/some-package/lib/cli.mjs
└── All fail → return { resolved: false, error: "..." }
```

## Procedure

### 1. Define the ResolvedPaths type

```typescript
interface ResolvedPaths {
  jiti: string;       // Resolved entry point path
  runner: string;     // Resolved runner script path
  resolved: boolean;  // Both resolved successfully
  error?: string;     // Error message if resolution failed
}
```

### 2. Implement Strategy Helpers

**Strategy 1: require.resolve (works for direct dependencies)**

```typescript
function resolveViaRequire(packageName: string): string | undefined {
  try {
    return require.resolve(`${packageName}/package.json`);
  } catch {
    return undefined;
  }
}
```

**Strategy 2: Walk from sibling module (works for peer dependencies)**

```typescript
function resolveViaSibling(siblingPackage: string, targetPackage: string): string | undefined {
  try {
    const siblingRoot = dirname(require.resolve(`${siblingPackage}/package.json`));
    const targetPath = resolve(siblingRoot, "node_modules", targetPackage, "package.json");
    if (existsSync(targetPath)) return targetPath;
  } catch {
    return undefined;  // Sibling not found — skip
  }
}
```

**Strategy 3: Hardcoded fallback (works for known install locations)**

```typescript
function resolveViaHardcoded(path: string): string | undefined {
  return existsSync(path) ? path : undefined;
}
```

### 3. Resolve the Entry Point from package.json bin

```typescript
function resolveEntryPoint(packageJsonPath: string): string | undefined {
  if (!existsSync(packageJsonPath)) return undefined;

  const pkg = JSON.parse(readFileSync(packageJsonPath, "utf-8"));
  const binField = pkg.bin;
  const binPath = typeof binField === "string"
    ? binField
    : binField?.jiti ?? Object.values(binField ?? {})[0];

  if (!binPath) return undefined;

  const packageRoot = dirname(packageJsonPath);
  const candidates = [binPath, "lib/jiti-cli.mjs"].filter(Boolean);
  
  for (const candidate of candidates) {
    const candidatePath = resolve(packageRoot, candidate);
    if (existsSync(candidatePath)) return candidatePath;
  }
  return undefined;
}
```

### 4. Compose into a Combined Resolver

```typescript
function resolveTargetPath(targetBin: string): string | undefined {
  const strategies: Array<() => string | undefined> = [
    // Strategy 1: Direct require.resolve
    () => {
      const pkgJson = resolveViaRequire(targetBin);
      return pkgJson ? resolveEntryPoint(pkgJson) : undefined;
    },
    // Strategy 2: Walk from sibling
    () => {
      const pkgJson = resolveViaSibling("pi-subagents", targetBin);
      return pkgJson ? resolveEntryPoint(pkgJson) : undefined;
    },
    // Strategy 3: Hardcoded fallback
    () => resolveViaHardcoded(`/root/.pi/agent/npm/node_modules/${targetBin}/lib/cli.mjs`),
  ];

  for (const strategy of strategies) {
    try {
      const result = strategy();
      if (result) return result;
    } catch {
      continue;  // Strategy threw — try next
    }
  }
  return undefined;
}
```

### 5. Provide Combined Resolution for All Required Paths

```typescript
function resolveAllPaths(): ResolvedPaths {
  const jiti = resolveTargetPath("jiti");
  const runner = resolveRunnerScript();  // Similar pattern for runner

  if (!jiti) {
    return { jiti: "", runner: runner ?? "", resolved: false, error: "jiti CLI not found" };
  }
  if (!runner) {
    return { jiti, runner: "", resolved: false, error: "runner script not found" };
  }
  return { jiti, runner, resolved: true };
}
```

## Pitfalls

1. **Bundled packages** — `require.resolve` may not work if the target package is bundled or not installed. Always have Strategy 2/3 as fallback.
2. **Different Node.js versions** — `require.resolve` resolution depends on `node_modules` layout (flat vs nested). The sibling strategy (Strategy 2) works for both npm and pnpm.
3. **Symlinked packages** — `existsSync` follows symlinks automatically, but `readFileSync(packageJsonPath)` may read a symlinked file — the resolved path may differ from the real path.
4. **Multiple matching strategies** — The first strategy that returns a value wins. Order them by reliability (most specific first).
5. **Stale hardcoded paths** — Strategy 3 paths may break after an update. Use them as a last resort and log a warning.

## Verification

- [ ] `resolveTargetPath("jiti")` returns a valid absolute path to jiti CLI
- [ ] When `require.resolve` throws (package not installed), Strategy 2 or 3 succeeds
- [ ] When all strategies fail, `resolved: false` is returned with a descriptive error
- [ ] `resolveEntryPoint(packageJsonPath)` correctly resolves bin field (string and object forms)
- [ ] Handles the case where package.json exists but has no bin field
- [ ] Returns `undefined` (not throws) when all strategies fail