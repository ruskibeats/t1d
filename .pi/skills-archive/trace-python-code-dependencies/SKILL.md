---
name: trace-python-code-dependencies
description: Trace class definitions, method declarations, type enums, and import dependencies across a Python codebase using ripgrep and read. Use when understanding module relationships, finding where types are defined vs used, or mapping out call graphs.
version: 1
created: 2026-05-19
updated: 2026-05-19
---
# Trace Python Code Dependencies

Procedure for tracing definitions, imports, and usage across a Python project using ripgrep and read.

## When to Use

- Understanding where a class, method, type enum, or function **is defined** vs **imported** vs **used**
- Mapping dependencies between modules (e.g., which service imports which type)
- Finding all callers of a method before refactoring
- Discovering import chains across a codebase
- Verifying type enum values and their usages

## Procedure

### 1. Find definitions (class, method, function)

```bash
# Method definition in class
rg "async def detect_overnight_hypoglycemia\b" --type py

# Class definition
rg "^class GraphEdgeType\b" --type py

# Function definition
rg "^def detect_spikes\b" --type py

# Enum member usage
rg "GraphEdgeType\.SLEEP_TO_NEXT_DAY_GLUCOSE" --type py
```

**Flags**: `-n` for line numbers, `--type py` for Python files only. Omit `--type` for multi-language projects.

### 2. Find all imports of a module type

```bash
rg "from app\.metrics\.types import" --type py -n
```

For specific types:
```bash
rg "from app\.metrics\.types import.*GraphEdgeType" --type py -n
rg "import.*GraphEdgeType" --type py -n
```

### 3. Resolve lazy/local imports

Some modules use deferred imports inside methods (to avoid circular imports):

```bash
# Look inside method bodies
rg "from app.metrics.graph_service import" --type py -n -A2
```

Read the surrounding context to understand the lazy-load pattern.

### 4. Trace method signature with context

```bash
# Find definition + 20 lines of context
rg -n "async def detect_overnight_hypoglycemia" --type py -A 20
```

### 5. Read the actual file for full understanding

```bash
# After rg finds it at line N
read app/services/pattern_service.py --offset N --limit 60
```

Combine with grep output to target the right region.

### 6. Map all type enums from a module

```bash
# List all enum members
rg "^\s+(class|def)\b" app/metrics/types.py -n
# Or read the whole file
read app/metrics/types.py
```

Then find every usage across the project:
```bash
rg "GraphEdgeType\." --type py -n
rg "MetricType\." --type py -n
```

### 7. Full dependency map for a type

For a type like `GraphEdgeType`:

```bash
# 1. Find definition
rg "^class GraphEdgeType" --type py -n

# 2. Find all imports
rg "import.*GraphEdgeType" --type py -n
rg "from.*import.*GraphEdgeType" --type py -n

# 3. Find all usages
rg "GraphEdgeType\\." --type py -n

# 4. Find where edges are created/instantiated
rg "edge_type=GraphEdgeType" --type py -n -B2 -A2
```

## Pitfalls

- **Lazy imports**: Some files import inside methods/functions rather than at the top. Grep for the import string (e.g., `from app.metrics.types import`) without restricting to top-level — check inside `try/except` blocks and method bodies too.
- **Type annotations in strings** (`from __future__ import annotations`): These are treated as strings and won't appear in import checks. Look for `TYPE_CHECKING` blocks.
- **Multiple files with same method name**: When `rg` returns hits in test files, exclude them with `--glob '!tests/'` or `--glob '!test_*'`.
- **Enum usage vs string literals**: If enums are used as string constants elsewhere, grep for the string value too (e.g., `"meal_to_glucose_spike"` vs `GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE`).
- **Circular imports**: If a file doesn't have a top-level import, it may be using deferred imports to break circular dependencies. Check method bodies.
- **Overlapping type names**: If two modules define types with the same name, include the full module path in the grep pattern.

## Verification

- After finding definitions, read the actual source to confirm signatures match.
- When patching/refactoring, count usages before and after to ensure completeness.
- Use `rg -c` (count mode) to quantify how many files reference a type.