---
name: survey-python-package-implementations
description: Survey and understand a Python package with multiple similar service/module implementations. Discover files, read the package init for exports, then read each module to identify common patterns, differences, and integration points. Use when exploring a new package, onboarding to a codebase area, or comparing multiple implementations of the same interface.
version: 1
created: 2026-05-19
updated: 2026-05-19
---
# Survey Python Package Implementations

Procedure for exploring a Python package with multiple similar implementations (e.g., ingestion services, API clients, data providers) to understand the common pattern, interface contract, and per-module differences.

## When to Use

- Onboarding to a codebase area that has multiple parallel implementations (e.g., 5 different ingestion services in a package)
- Understanding the shared interface/pattern across modules that implement the same abstract contract
- Comparing implementations to find inconsistencies, missing features, or drift from the common pattern
- Before adding a new implementation to an existing set of similar modules
- Auditing whether all modules follow the same conventions (imports, error handling, method signatures)

Do **not** use this skill when:
- You only need to trace a single definition or import — use `trace-python-code-dependencies`
- You only need to read the docstring of one file — just `read` it directly
- You need to search for a specific string across the codebase — use `rg`

## Procedure

### 1. Discover files in the package directory

```bash
ls <package_directory>/
```

Or for a richer view including sizes and timestamps:
```bash
ls -la <package_directory>/
```

Example: `ls app/ingestion/` reveals the set of service files: `garmin.py`, `fitbit.py`, `withings.py`, etc.

### 2. Read the package `__init__.py`

The `__init__.py` reveals:
- What is **exported** via `__all__`
- Public class/function names
- Package-level docstring with high-level purpose

```bash
read <package_directory>/__init__.py
```

### 3. Read the first module completely

Pick the most representative implementation (often the first alphabetically or the most complex). Read the full file to establish the **base pattern**:

```bash
read <package_directory>/<first_module>.py
```

Note down:
- Class name and constructor signature (`__init__` parameters)
- Base URL or configuration constants
- Method signatures (especially any shared interface like `fetch()`, `sync()`, `normalize()`)
- Import patterns (lazy vs top-level imports)
- Error handling approach
- Return type shape (usually a shared schema/dataclass)

### 4. Read the remaining modules for comparison

For each remaining module, read the file to identify:
- Does it follow the same class/constructor pattern?
- Does it return the same schema types?
- Are there additional features/edge cases unique to this provider?
- Are there missing fields, different error handling, or different data shapes?

```bash
read <package_directory>/<remaining_modules>.py
```

### 5. Summarize the common pattern

After reading all modules, articulate:
- **Shared interface**: Every implementation's public API
- **Per-provider differences**: Unique fields, auth flows, data mapping quirks
- **Gaps**: Modules that don't implement the full interface, or missing providers
- **Consistency issues**: Different error handling styles, different import patterns, different type hints

### 6. (Optional) Verify against shared types

If the implementations share a common schema/type module, read it to confirm understanding:

```bash
# Find the shared types
rg "from.*import.*(HealthMetricCreate|MetricType)" <package_directory>/<module>.py -n | head -5

# Read the shared types
read app/metrics/types.py
read app/metrics/schemas.py
```

## Pitfalls

- **Missing `__init__.py` exports**: Some modules exist in the directory but aren't exported via `__all__`. Always check by listing the directory AND reading the init.
- **Subdirectories**: The package might have sub-packages (`package/subdir/__init__.py`). Use `ls -R` to discover nested structure.
- **Circular imports**: Modules may use lazy imports inside methods rather than top-level imports. Check method bodies for `from X import Y` inside function/method definitions.
- **Abstract base classes**: The common interface may be enforced via an ABC or protocol in a separate file, not in the individual modules. Search for `abc.ABC`, `@abstractmethod`, or `Protocol` in the package.
- **Incomplete implementations**: Some modules may be stubs or partially implemented. Look for `raise NotImplementedError`, `pass` as method body, or `TODO`/`FIXME` comments.
- **Different constructor signatures**: Even if the public methods are the same, constructors may differ (e.g., some need `access_token`, others need `client_id` + `client_secret`). Document these differences.
- **Different return shapes**: While all may return the same schema type, some may return lists vs single objects, or use different date formats. Check using `rg` for the schema constructor calls.

## Verification

- You can name the shared interface pattern (constructor params, method signatures, return type) across all modules
- You identified at least one meaningful difference between implementations
- You can answer: "If I add a new module to this package, what methods must it implement and what should it return?"
- (Optional) `rg "class \w+Service" <package_directory>/ -n` — confirms all service classes are discovered
- (Optional) `rg "raises? " <package_directory>/ -n` — reveals which modules have proper error handling vs silent failures