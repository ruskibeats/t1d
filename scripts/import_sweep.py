#!/usr/bin/env python3
"""Import Sweep — validates every app module can be imported cleanly.

Iterates over all Python modules in ``app/``, imports each one in a
try/except block, and reports failures in a single pass.  Does *not*
require a database, Docker, or a running server.

Usage::

    python3 scripts/import_sweep.py

Exit code: 0 if all imports succeed, 1 if any failures.
"""

import importlib
import pathlib
import sys
import traceback
from typing import List, Tuple

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def _walk_modules(root: pathlib.Path) -> List[str]:
    """Return all dotted module paths under *root* (e.g. ``app.config``)."""
    modules: List[str] = []

    # Only import from app/
    for path in root.rglob("*.py"):
        if path.name == "__main__.py":
            continue
        if ".agents" in path.parts or ".pi" in path.parts:
            continue
        if "migrations" in path.parts:
            continue
        if path.name.startswith("_"):
            # Only include __init__.py if the package also has other modules
            # (avoid importing empty __init__ packages)
            if path.name == "__init__.py":
                # Always include __init__.py for app packages
                pass
            else:
                continue

        # Convert filesystem path to dotted module path
        rel = path.relative_to(root.parent)  # relative to project root
        dotted = ".".join(rel.with_suffix("").parts)
        modules.append(dotted)

    return sorted(set(modules))


def _import_one(dotted: str) -> Tuple[bool, str]:
    """Try importing *dotted* and return ``(ok, details)``."""
    try:
        importlib.import_module(dotted)
        return True, "OK"
    except Exception as exc:
        tb = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        return False, tb


def main() -> int:
    # Ensure project root is on sys.path
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    modules = _walk_modules(PROJECT_ROOT / "app")
    print(f"Found {len(modules)} modules to check\n")

    failures: List[Tuple[str, str]] = []
    successes = 0

    for module in modules:
        ok, details = _import_one(module)
        if ok:
            successes += 1
            print(f"  ✓  {module}")
        else:
            failures.append((module, details))
            print(f"  ✗  {module}")

    print(f"\n{'='*60}")
    print(f"Results: {successes} passed, {len(failures)} failed")
    print(f"{'='*60}\n")

    if failures:
        print("FAILURES:\n")
        for module, details in failures:
            print(f"  {module}:")
            for line in details.split("\n"):
                print(f"    {line}")
            print()

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())