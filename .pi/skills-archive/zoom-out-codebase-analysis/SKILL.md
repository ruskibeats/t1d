---
name: "zoom-out-codebase-analysis"
description: "Provide a high-level architectural overview of a codebase by discovering domain docs and ADRs"
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
When asked to "zoom out" on a codebase, provide architectural context, or understand how components fit together. Especially useful for new contributors or when context-switching into an unfamiliar project.

## Procedure

1. **Start with the scaffold** - Provide a high-level overview:
   - Main layers (backend/frontend/data/infrastructure)
   - Key directories and their purposes
   - Entry points and data flow

2. **Discover domain documentation**:
   - Look for `docs/`, `ADR/`, or similar documentation folders
   - Find domain language, architecture decisions, system overviews
   - Read 2-3 most recent/relevant docs

3. **Map to actual code**:
   - Cross-reference docs with actual file structure
   - Identify key modules, services, and their relationships
   - Note any gaps between documented and actual architecture

4. **Summarize findings**:
   - Layer-by-layer breakdown
   - Key integration points
   - Data flow paths
   - Notable patterns (service layer, repository, etc.)

## Pitfalls to Avoid
- Don't dive into implementation details - stay at the architectural layer
- Don't make assumptions about undocumented areas
- Always cross-check documentation against actual code

## Verification
- Verify all mentioned directories/exits actually exist
- Confirm ADR numbers and dates are accurate
- Check that layer boundaries reflect actual code structure