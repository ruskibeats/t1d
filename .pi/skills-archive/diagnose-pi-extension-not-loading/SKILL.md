---
name: "diagnose-pi-extension-not-loading"
description: "Diagnose why a Pi extension isn't loading — check file structure, package.json, dependencies, discovery paths, pi config, and pi version. Use when a pi extension fails to register commands/tools or doesn't appear to be active."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Diagnose a Pi Extension That Isn't Loading

## When to Use
A Pi extension isn't loading — its commands, tools, or UI widgets aren't available. Use this procedure to systematically find the root cause.

## Procedure

### 1. Verify Extension File Structure
```bash
# Check the extension directory exists and has expected files
ls -la .pi/extensions/<name>/
# Expected: index.ts (or .js), package.json, plus component files
```

### 2. Check package.json Registration
```bash
# Read the extension's package.json
cat .pi/extensions/<name>/package.json
```
- Must have `"pi": {"extensions": ["./index.ts"]}` (or ./index.js)
- Entry point path is relative to the extension directory
- `"type": "module"` is required for ESM-based extensions

### 3. Check Dependencies (most common cause)
```bash
# Check if node_modules exists
ls .pi/extensions/<name>/node_modules/ 2>&1

# Check for lockfile
ls .pi/extensions/<name>/package-lock.json 2>&1
ls .pi/extensions/<name>/yarn.lock 2>&1
```
- If `node_modules/` is missing, the extension's imports will fail
- Run `cd .pi/extensions/<name> && npm install` to install deps
- Example: imports of `@earendil-works/pi-coding-agent` and `@earendil-works/pi-tui` require those to be installed

### 4. Check if Extension is Discovered
```bash
# List installed packages (shows npm-installed packages)
pi list

# Check if extension entry point compiles (look for TS errors)
# Try importing the entry point to check for syntax/import errors
```

### 5. Check Pi Configuration
```bash
# Find pi config directory
ls -la ~/.config/pi/

# Read settings (may have extension-related config)
cat ~/.config/pi/agent/settings.json

# Check for extension-specific config files
```

### 6. Check Pi Version
```bash
pi --version
```
- Older versions may not support certain extension features
- Extension API types come from `@earendil-works/pi-coding-agent` — ensure version compatibility

### 7. Check Compiled Entry Point
```bash
# For .ts extensions, check if TypeScript compiles
# Read index.ts imports and trace them
head -30 .pi/extensions/<name>/index.ts

# Check each import resolves
# - @earendil-works/pi-coding-agent types
# - @earendil-works/pi-tui TUI types
# - Local relative imports (./state/*, ./tool/*, etc.)
```

### 8. Check for Error Messages
```bash
# Try starting pi with debug/verbose logging if available
# Look for startup errors in pi's own logs
# Extensions failing to load typically print errors to stderr during `pi` startup
```

### 9. Verify File Permissions
```bash
ls -la .pi/extensions/<name>/index.ts
# Ensure readable by the pi process user
```

## Pitfalls
- **Missing `node_modules/`** is the #1 cause — the extension may have needed peer deps like `@earendil-works/pi-coding-agent` which aren't installed
- **`pi list` does NOT show project-local extensions** in `.pi/extensions/` — it only shows npm-installed packages. Don't assume an extension isn't loading just because it's absent from `pi list`
- **TypeScript compilation errors** in .ts entry points can silently prevent loading — there's no compilation step shown by default
- **`"type": "module"` is required** in package.json for ESM-based extensions
- **Hoisted dependencies**: if `node_modules/` exists but a dep is hoisted to a parent directory, it may still resolve. Check the project root's node_modules as well
- **Auth/token config**: some extensions (like clanker-ops) have independent config files (~/.config/rpiv-todo/config.json or similar) — check those too

## Verification
1. ✅ All expected files exist in `.pi/extensions/<name>/`
2. ✅ `package.json` has valid `"pi": {"extensions": [...]}` entry
3. ✅ `node_modules/` exists with required dependencies installed
4. ✅ Extension entry point compiles without import errors
5. ✅ No TypeScript syntax errors in source files
6. ✅ File permissions allow reading by pi process
7. ✅ Pi version is recent enough to support the extension features